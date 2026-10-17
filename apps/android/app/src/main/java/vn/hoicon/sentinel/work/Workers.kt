package vn.hoicon.sentinel.work

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import java.util.concurrent.TimeUnit
import vn.hoicon.rules.RiskEngine
import vn.hoicon.sentinel.BuildConfig
import vn.hoicon.sentinel.SentinelServices
import vn.hoicon.sentinel.data.local.TokenStorage
import vn.hoicon.sentinel.data.outbox.FlushOutcome
import vn.hoicon.sentinel.data.drill.DrillCheck
import vn.hoicon.sentinel.data.drill.DrillInvitation
import vn.hoicon.sentinel.data.drill.PrefsDrillStore
import vn.hoicon.sentinel.data.remote.DrillApiClient
import vn.hoicon.sentinel.data.remote.DrillResultOutcome
import vn.hoicon.sentinel.data.remote.DrillStatus
import vn.hoicon.sentinel.data.remote.ElderAnswer
import vn.hoicon.sentinel.data.remote.ElderAnswerResult
import vn.hoicon.sentinel.data.remote.ElderApiClient
import vn.hoicon.sentinel.data.remote.HeartbeatResult
import vn.hoicon.sentinel.data.remote.HeartbeatStatus
import vn.hoicon.sentinel.data.remote.PairingApiClient
import vn.hoicon.sentinel.data.threat.ThreatSyncOutcome
import vn.hoicon.sentinel.domain.drill.DrillAnswer
import vn.hoicon.sentinel.domain.drill.DrillAnswers
import vn.hoicon.sentinel.domain.drill.DrillTiming
import vn.hoicon.sentinel.domain.rules.RiskWindowManager
import vn.hoicon.sentinel.sensing.Notifications
import vn.hoicon.sentinel.sensing.SensorPermission
import vn.hoicon.sentinel.sensing.SensorPermissions

private val needsNetwork = Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()

/**
 * Sends the queued risk events when there is a network (Spec 022 FR-002). Retries use WorkManager's exponential
 * backoff. Never part of the safe pause: that path does not wait for, or even know about, this worker.
 */
class OutboxWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = try {
        when (SentinelServices.of(applicationContext).flushOutbox()) {
            FlushOutcome.EMPTY -> Result.success()
            // Not paired yet / token refused: nothing a retry can fix. Pairing or the next event kicks it again.
            FlushOutcome.WAITING -> Result.success()
            // The family cannot be reached with this token any more: E6 asks the person to connect again.
            FlushOutcome.TOKEN_REFUSED -> {
                TokenStorage.create(applicationContext).needsRepair = true
                Result.success()
            }
            // A consent was withdrawn: the pairing is fine, so keep the token (no "reconnect") and let the queue wait.
            FlushOutcome.CONSENT_REQUIRED -> Result.success()
            FlushOutcome.RETRY -> Result.retry()
        }
    } catch (e: Exception) {
        if (e is kotlin.coroutines.cancellation.CancellationException) throw e
        Result.retry()
    }
}

object OutboxScheduler {
    private const val NOW = "hoicon-outbox"
    private const val PERIODIC = "hoicon-outbox-periodic"

    /**
     * Try to send soon. REPLACE, not APPEND: a worker waiting out a long backoff must not hold up an event that
     * arrives once the network is back. The short initial delay makes REPLACE a debounce: the several events of one
     * pause (opened, detected, shown…) go out in one request, and a down server is not hit once per event.
     */
    fun kick(context: Context) {
        val request = OneTimeWorkRequestBuilder<OutboxWorker>()
            .setInitialDelay(KICK_DELAY_SECONDS, TimeUnit.SECONDS)
            .setConstraints(needsNetwork)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, BACKOFF_SECONDS, TimeUnit.SECONDS)
            .build()
        WorkManager.getInstance(context).enqueueUniqueWork(NOW, ExistingWorkPolicy.REPLACE, request)
    }

    /** Safety net: a pass every 15 minutes whatever happened to the one-time requests. Idempotent. */
    fun schedulePeriodic(context: Context) {
        val request = PeriodicWorkRequestBuilder<OutboxWorker>(15, TimeUnit.MINUTES)
            .setConstraints(needsNetwork)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, BACKOFF_SECONDS, TimeUnit.SECONDS)
            .build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(PERIODIC, ExistingPeriodicWorkPolicy.KEEP, request)
    }

    private const val BACKOFF_SECONDS = 30L
    private const val KICK_DELAY_SECONDS = 3L
}

/** Every 15 minutes: which permissions are granted and which versions run, so the family learns of lost protection. */
class HeartbeatWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = try {
        val tokens = TokenStorage.create(applicationContext)
        val session = tokens.load()
        if (session == null || !SentinelServices.of(applicationContext).mayShare()) {
            Result.success()
        } else {
            val services = SentinelServices.of(applicationContext)
            val granted = SensorPermissions.granted(applicationContext)
            val status = HeartbeatStatus(
                appVersion = BuildConfig.VERSION_NAME,
                rulesVersion = RiskEngine.VERSION,
                threatListVersion = services.database.threats().latestVersion(),
                permissionState = SensorPermission.entries.associate { it.name.lowercase() to (it in granted) },
            )
            when (PairingApiClient(BuildConfig.API_BASE_URL).sendHeartbeat(session.accessToken, status)) {
                HeartbeatResult.NetworkError, HeartbeatResult.ServerError -> Result.retry()
                HeartbeatResult.Unauthorized -> {
                    TokenStorage.create(applicationContext).needsRepair = true
                    Result.success()
                }
                // Consent withdrawn: keep the pairing as it is; the next period tries again once consent is given.
                HeartbeatResult.ConsentWithdrawn -> Result.success()
                // Refused body: a retry cannot fix it; the next period tries again.
                HeartbeatResult.Ok, HeartbeatResult.Rejected -> {
                    askForDrill(session.accessToken)
                    Result.success()
                }
            }
        }
    } catch (e: Exception) {
        if (e is kotlin.coroutines.cancellation.CancellationException) throw e
        Result.retry()
    }
}

/**
 * Spec 028 FR-008: after a good heartbeat, ask whether the family scheduled a practice drill. Whatever happens here (no
 * network, a server error, a script that does not parse) never changes the heartbeat's own result: the next beat asks again.
 */
private suspend fun HeartbeatWorker.askForDrill(accessToken: String) {
    try {
        val services = SentinelServices.of(applicationContext)
        val store = PrefsDrillStore(applicationContext)
        val windowOpen: suspend () -> Boolean = { RiskWindowManager.isOpen(services.database.riskWindow().get(), System.currentTimeMillis()) }
        val invitation = DrillInvitation(DrillApiClient(BuildConfig.API_BASE_URL), store, services::mayShare, windowOpen)
        when (val check = invitation.check(accessToken)) {
            is DrillCheck.Invite -> {
                // The risk window may have opened while the server was answering: look again right before showing anything.
                if (check.firstTime && !windowOpen()) {
                    val shown = Notifications.showDrillInvitation(applicationContext, DrillTiming.millisUntil(check.offer.windowEnd))
                    if (shown) store.notifiedDrillId = check.offer.drillId
                }
            }
            DrillCheck.Unauthorized -> TokenStorage.create(applicationContext).needsRepair = true
            DrillCheck.NotAllowed, DrillCheck.Deferred, DrillCheck.Nothing, DrillCheck.Failed -> Unit
        }
    } catch (e: Exception) {
        if (e is kotlin.coroutines.cancellation.CancellationException) throw e
    }
}

object HeartbeatScheduler {
    private const val NAME = "hoicon-heartbeat"

    /** Idempotent: call on every app start once the device is paired. */
    fun schedule(context: Context) {
        val request = PeriodicWorkRequestBuilder<HeartbeatWorker>(15, TimeUnit.MINUTES)
            .setConstraints(needsNetwork)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 60, TimeUnit.SECONDS)
            .build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(NAME, ExistingPeriodicWorkPolicy.KEEP, request)
    }
}

/**
 * Keeps the on-device threat list fresh (Spec 026 FR-010): `GET /v1/threat-list?since=`, `304` when unchanged, and a bad
 * download leaves the list in force. Only needs a paired device; carries nothing about the person. Never part of the
 * safe pause.
 */
class ThreatSyncWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = try {
        val session = TokenStorage.create(applicationContext).load()
        if (session == null) {
            Result.success()
        } else {
            when (SentinelServices.of(applicationContext).threatSyncer.sync(session.accessToken)) {
                ThreatSyncOutcome.RETRY -> Result.retry()
                ThreatSyncOutcome.UNAUTHORIZED -> {
                    TokenStorage.create(applicationContext).needsRepair = true
                    Result.success()
                }
                // Updated, unchanged, a download that failed validation (the old list stays) or rate-limited today:
                // nothing a retry can fix; the next period tries again.
                ThreatSyncOutcome.UPDATED, ThreatSyncOutcome.NOT_MODIFIED, ThreatSyncOutcome.KEPT_OLD, ThreatSyncOutcome.LATER -> Result.success()
            }
        }
    } catch (e: Exception) {
        if (e is kotlin.coroutines.cancellation.CancellationException) throw e
        Result.retry()
    }
}

object ThreatSyncScheduler {
    private const val PERIODIC = "hoicon-threat-sync-periodic"
    private const val NOW = "hoicon-threat-sync-now"
    private const val BACKOFF_SECONDS = 60L

    /** Every 12 hours, plus one pass now (opening the app, finishing pairing). KEEP: idempotent, never piles up. */
    fun schedule(context: Context) {
        val manager = WorkManager.getInstance(context)
        val periodic = PeriodicWorkRequestBuilder<ThreatSyncWorker>(12, TimeUnit.HOURS)
            .setConstraints(needsNetwork)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, BACKOFF_SECONDS, TimeUnit.SECONDS)
            .build()
        manager.enqueueUniquePeriodicWork(PERIODIC, ExistingPeriodicWorkPolicy.KEEP, periodic)
        val now = OneTimeWorkRequestBuilder<ThreatSyncWorker>()
            .setConstraints(needsNetwork)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, BACKOFF_SECONDS, TimeUnit.SECONDS)
            .build()
        manager.enqueueUniqueWork(NOW, ExistingWorkPolicy.KEEP, now)
    }
}

/**
 * Sends one E8 answer (spec 024 FR-009). The screen closes at once; this worker retries with backoff until the server
 * has it. Only ids and the yes/no/unsure enum travel (ADR-009). A late answer comes back "expired": the server timer
 * already moved on, so there is nothing left to retry.
 */
class ElderAnswerWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = try {
        val incidentId = inputData.getString(INCIDENT_ID)
        val questionId = inputData.getString(QUESTION_ID)
        val answer = inputData.getString(ANSWER)
        val session = TokenStorage.create(applicationContext).load()
        if (incidentId == null || questionId == null || answer == null || session == null) {
            Result.success()
        } else {
            val result = ElderApiClient(BuildConfig.API_BASE_URL)
                .submitAnswer(session.accessToken, incidentId, ElderAnswer(questionId, answer))
            if (result is ElderAnswerResult.Unauthorized) TokenStorage.create(applicationContext).needsRepair = true
            if (elderAnswerNeedsRetry(result)) Result.retry() else Result.success()
        }
    } catch (e: Exception) {
        if (e is kotlin.coroutines.cancellation.CancellationException) throw e
        Result.retry()
    }

    companion object {
        const val INCIDENT_ID = "incident_id"
        const val QUESTION_ID = "question_id"
        const val ANSWER = "answer"
    }
}

/** Only transport failures are worth another try; every answer the server understood is final. */
fun elderAnswerNeedsRetry(result: ElderAnswerResult): Boolean =
    result is ElderAnswerResult.NetworkError || result is ElderAnswerResult.ServerError

object ElderAnswerScheduler {
    /** KEEP: the first button pressed for an incident wins; a second tap (or the timeout) does not overwrite it. */
    fun submit(context: Context, incidentId: String, questionId: String, answer: String) {
        val request = OneTimeWorkRequestBuilder<ElderAnswerWorker>()
            .setInputData(
                workDataOf(
                    ElderAnswerWorker.INCIDENT_ID to incidentId,
                    ElderAnswerWorker.QUESTION_ID to questionId,
                    ElderAnswerWorker.ANSWER to answer,
                ),
            )
            .setConstraints(needsNetwork)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, BACKOFF_SECONDS, TimeUnit.SECONDS)
            .build()
        WorkManager.getInstance(context)
            .enqueueUniqueWork("hoicon-elder-answer-$incidentId", ExistingWorkPolicy.KEEP, request)
    }

    private const val BACKOFF_SECONDS = 10L
}

/** What to do with the answer to one drill-result upload. */
enum class DrillResultAction { DONE, RETRY, DROP }

/**
 * `2xx` and `409` are done (the server holds a result for this drill); only transport trouble and 5xx are worth another
 * try. Everything else is final: the server understood the request and said no (or the token is gone: E6 asks to reconnect).
 */
fun drillResultAction(outcome: DrillResultOutcome): DrillResultAction = when (outcome) {
    DrillResultOutcome.Accepted -> DrillResultAction.DONE
    DrillResultOutcome.NetworkError, DrillResultOutcome.ServerError -> DrillResultAction.RETRY
    DrillResultOutcome.Unauthorized, DrillResultOutcome.NotFound, DrillResultOutcome.Rejected -> DrillResultAction.DROP
}

/**
 * Sends how a drill ended (Spec 028 FR-009). The screen closes at once; this worker retries with backoff until the
 * server has it, and gives up only when the server says it never will. Only the status and the letters of the choices
 * travel, never text (SC-006).
 */
class DrillResultWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = try {
        val drillId = inputData.getString(DRILL_ID)
        val status = DrillStatus.entries.firstOrNull { it.wire == inputData.getString(STATUS) }
        val session = TokenStorage.create(applicationContext).load()
        // Consent withdrawn (or never given) since the drill was played: nothing about it leaves the phone.
        if (drillId == null || status == null || session == null || !SentinelServices.of(applicationContext).mayShare()) {
            Result.success()
        } else {
            val outcome = DrillApiClient(BuildConfig.API_BASE_URL).sendResult(
                session.accessToken,
                drillId,
                status,
                DrillAnswers.decode(inputData.getString(ANSWERS)),
                inputData.getString(STARTED_AT),
                inputData.getString(COMPLETED_AT),
            )
            if (outcome is DrillResultOutcome.Unauthorized) TokenStorage.create(applicationContext).needsRepair = true
            when (drillResultAction(outcome)) {
                DrillResultAction.DONE -> Result.success()
                DrillResultAction.RETRY -> Result.retry()
                DrillResultAction.DROP -> Result.failure()
            }
        }
    } catch (e: Exception) {
        if (e is kotlin.coroutines.cancellation.CancellationException) throw e
        Result.retry()
    }

    companion object {
        const val DRILL_ID = "drill_id"
        const val STATUS = "status"
        const val ANSWERS = "answers"
        const val STARTED_AT = "started_at"
        const val COMPLETED_AT = "completed_at"
    }
}

object DrillResultScheduler {
    /** KEEP: the first result for a drill wins; a second tap or a restarted screen does not queue another. */
    fun submit(
        context: Context,
        drillId: String,
        status: DrillStatus,
        answers: List<DrillAnswer>,
        startedAt: String? = null,
        completedAt: String? = null,
    ) {
        val request = OneTimeWorkRequestBuilder<DrillResultWorker>()
            .setInputData(
                workDataOf(
                    DrillResultWorker.DRILL_ID to drillId,
                    DrillResultWorker.STATUS to status.wire,
                    DrillResultWorker.ANSWERS to DrillAnswers.encode(answers),
                    DrillResultWorker.STARTED_AT to startedAt,
                    DrillResultWorker.COMPLETED_AT to completedAt,
                ),
            )
            .setConstraints(needsNetwork)
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, BACKOFF_SECONDS, TimeUnit.SECONDS)
            .build()
        WorkManager.getInstance(context)
            .enqueueUniqueWork("hoicon-drill-result-$drillId", ExistingWorkPolicy.KEEP, request)
    }

    private const val BACKOFF_SECONDS = 30L
}

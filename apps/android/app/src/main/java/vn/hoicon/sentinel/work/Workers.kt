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
import vn.hoicon.sentinel.data.remote.ElderAnswer
import vn.hoicon.sentinel.data.remote.ElderAnswerResult
import vn.hoicon.sentinel.data.remote.ElderApiClient
import vn.hoicon.sentinel.data.remote.HeartbeatResult
import vn.hoicon.sentinel.data.remote.HeartbeatStatus
import vn.hoicon.sentinel.data.remote.PairingApiClient
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
        val session = TokenStorage.create(applicationContext).load()
        if (session == null) {
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
                // Refused body: a retry cannot fix it; the next period tries again.
                HeartbeatResult.Ok, HeartbeatResult.Rejected -> Result.success()
            }
        }
    } catch (e: Exception) {
        if (e is kotlin.coroutines.cancellation.CancellationException) throw e
        Result.retry()
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

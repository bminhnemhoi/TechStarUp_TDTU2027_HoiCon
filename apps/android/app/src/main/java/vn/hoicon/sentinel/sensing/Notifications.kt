package vn.hoicon.sentinel.sensing

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.compose.ui.graphics.toArgb
import vn.hoicon.sentinel.DrillActivity
import vn.hoicon.sentinel.MainActivity
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.pause.PauseRequest
import vn.hoicon.sentinel.pause.SafePauseActivity
import vn.hoicon.sentinel.ui.theme.HoiConTokens

/**
 * Channels: "đang để ý giúp bác" for the risk-window FGS (default importance but silent ⇒ status-bar icon, UX-8),
 * high importance for the fallback when SafePause can't open. Every notification carries the AI disclosure as
 * subText (CLAUDE.md rule 6; checked by rules/AiDisclosureCopyTest).
 */
object Notifications {
    const val ID_PROTECTING = 1
    private const val ID_PAUSE_FALLBACK = 2
    private const val ID_ELDER_QUESTION = 4
    private const val ID_DRILL = 3

    // Channel importance can't be raised after creation: the LOW channel of the first spike build is replaced.
    private const val OLD_CHANNEL_PROTECTING = "protecting"
    private const val CHANNEL_PROTECTING = "protecting_v2"
    private const val CHANNEL_PAUSE = "safe_pause"
    private const val CHANNEL_DRILLS = "drills"

    private fun manager(context: Context) = context.getSystemService(NotificationManager::class.java)

    fun ensureChannels(context: Context) {
        val manager = manager(context)
        manager.deleteNotificationChannel(OLD_CHANNEL_PROTECTING)
        val protecting = NotificationChannel(
            CHANNEL_PROTECTING,
            context.getString(R.string.channel_protecting),
            NotificationManager.IMPORTANCE_DEFAULT,
        ).apply {
            // UX-8 "silent": visible (status-bar icon) but no sound/vibration — the channel equivalent of
            // NotificationCompat.setSilent(true) (the platform builder has no setSilent). DEFAULT never peeks.
            setSound(null, null)
            enableVibration(false)
        }
        val pause = NotificationChannel(
            CHANNEL_PAUSE,
            context.getString(R.string.channel_pause),
            NotificationManager.IMPORTANCE_HIGH,
        )
        // Spec 028: a plain invitation. Default importance (never a heads-up, never urgent), no full-screen intent anywhere.
        val drills = NotificationChannel(
            CHANNEL_DRILLS,
            context.getString(R.string.channel_drills),
            NotificationManager.IMPORTANCE_DEFAULT,
        )
        manager.createNotificationChannels(listOf(protecting, pause, drills))
    }

    /** Ongoing notification of the risk-window FGS: shown at once, not after the 10 s FGS delay. */
    fun protecting(context: Context): Notification {
        ensureChannels(context)
        val open = PendingIntent.getActivity(
            context,
            0,
            Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE,
        )
        val text = context.getString(R.string.protecting_text)
        return Notification.Builder(context, CHANNEL_PROTECTING)
            .setSmallIcon(R.drawable.ic_stat_shield)
            .setContentTitle(context.getString(R.string.protecting_title))
            .setContentText(text)
            .setStyle(Notification.BigTextStyle().bigText(text))
            .setSubText(context.getString(R.string.notif_ai_subtext))
            .setCategory(Notification.CATEGORY_SERVICE)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(open)
            .apply {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    setForegroundServiceBehavior(Notification.FOREGROUND_SERVICE_IMMEDIATE)
                }
            }
            .build()
    }

    /**
     * P1-S2 experiment (ADR-008): only the debug manifest declares USE_FULL_SCREEN_INTENT (Play grants it to calling
     * and alarm apps only on Android 14+). Even when allowed, an unlocked device gets a heads-up, not the activity.
     */
    private fun canUseFullScreenIntent(context: Context): Boolean =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            manager(context).canUseFullScreenIntent()
        } else {
            context.checkSelfPermission(Manifest.permission.USE_FULL_SCREEN_INTENT) == PackageManager.PERMISSION_GRANTED
        }

    /** Fallback when the background activity start was blocked (no "display over other apps"): heads-up + tap. */
    fun showPauseFallback(context: Context, request: PauseRequest) {
        ensureChannels(context)
        val tap = PendingIntent.getActivity(
            context,
            1,
            SafePauseActivity.intent(context, request),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        // Spike: the action opens the dialer, like the E7 button. P2-06 replaces it with the "Hỏi con" flow.
        val callChild = PendingIntent.getActivity(
            context,
            2,
            Intent(Intent.ACTION_DIAL).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = Notification.Builder(context, CHANNEL_PAUSE)
            .setSmallIcon(R.drawable.ic_stat_shield)
            .setContentTitle(context.getString(R.string.fallback_title))
            .setContentText(context.getString(R.string.fallback_text))
            .setStyle(Notification.BigTextStyle().bigText(context.getString(R.string.fallback_big_text)))
            .setSubText(context.getString(R.string.notif_ai_subtext))
            .setCategory(Notification.CATEGORY_REMINDER)
            .setContentIntent(tap)
            .apply { if (canUseFullScreenIntent(context)) setFullScreenIntent(tap, true) }
            .addAction(
                Notification.Action.Builder(null, context.getString(R.string.pause_call_child), callChild).build(),
            )
            .setAutoCancel(true)
            .build()
        HcSpikeLog.i("fallback notification fsi=${canUseFullScreenIntent(context)}")
        try {
            manager(context).notify(ID_PAUSE_FALLBACK, notification)
        } catch (e: SecurityException) {
            HcSpikeLog.w("fallback notification refused (POST_NOTIFICATIONS?)", e)
        }
    }

    /** The AI's question for the person when E8 could not open by itself (no "display over other apps"): heads-up on the safe-pause channel; touching it opens E8. */
    fun showElderQuestion(context: Context, open: Intent) {
        ensureChannels(context)
        val tap = PendingIntent.getActivity(context, 3, open.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val notification = Notification.Builder(context, CHANNEL_PAUSE)
            .setSmallIcon(R.drawable.ic_stat_shield)
            .setContentTitle(context.getString(R.string.elder_question_title))
            .setContentText(context.getString(R.string.elder_question_text))
            .setSubText(context.getString(R.string.notif_ai_subtext))
            .setCategory(Notification.CATEGORY_REMINDER)
            .setContentIntent(tap)
            .setAutoCancel(true)
            .build()
        try {
            manager(context).notify(ID_ELDER_QUESTION, notification)
        } catch (e: SecurityException) {
            HcSpikeLog.w("question notification refused (POST_NOTIFICATIONS?)", e)
        }
    }

    /**
     * The invitation to a practice drill (Spec 028 FR-008): an ordinary notification, labelled `[DIỄN TẬP]` in its title,
     * with no sound of its own beyond the channel default and no full-screen intent. Tapping it opens E11. True when it
     * could really be shown (notifications allowed), so the caller only then counts it as "notified".
     */
    fun showDrillInvitation(context: Context, timeoutMs: Long? = null): Boolean {
        ensureChannels(context)
        val open = PendingIntent.getActivity(
            context,
            3,
            DrillActivity.intent(context),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val text = context.getString(R.string.drill_notif_text)
        val notification = Notification.Builder(context, CHANNEL_DRILLS)
            // Its own icon and colour (never the shield of a real warning): a practice drill must not look like a real alert.
            .setSmallIcon(R.drawable.ic_drill_school)
            .setColor(HoiConTokens.Colors.DrillFg.toArgb())
            .setContentTitle(context.getString(R.string.drill_notif_title))
            .setContentText(text)
            .setStyle(Notification.BigTextStyle().bigText(text))
            .setSubText(context.getString(R.string.notif_ai_subtext))
            .setCategory(Notification.CATEGORY_REMINDER)
            .setContentIntent(open)
            .setAutoCancel(true)
            // The invitation is only good until the drill's window ends.
            .apply { if (timeoutMs != null && timeoutMs > 0) setTimeoutAfter(timeoutMs) }
            .build()
        return try {
            manager(context).notify(ID_DRILL, notification)
            manager(context).areNotificationsEnabled()
        } catch (e: SecurityException) {
            HcSpikeLog.w("drill invitation refused (POST_NOTIFICATIONS?)", e)
            false
        }
    }

    fun cancelDrillInvitation(context: Context) = manager(context).cancel(ID_DRILL)
}

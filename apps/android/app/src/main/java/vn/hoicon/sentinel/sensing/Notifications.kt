package vn.hoicon.sentinel.sensing

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import vn.hoicon.rules.AppCategory
import vn.hoicon.rules.RiskLevel
import vn.hoicon.sentinel.MainActivity
import vn.hoicon.sentinel.R
import vn.hoicon.sentinel.pause.SafePauseActivity

/**
 * Channels: "đang để ý giúp bác" for the risk-window FGS (default importance but silent ⇒ status-bar icon, UX-8),
 * high importance for the fallback when SafePause can't open. Every notification carries the AI disclosure as
 * subText (CLAUDE.md rule 6; checked by rules/AiDisclosureCopyTest).
 */
object Notifications {
    const val ID_PROTECTING = 1
    private const val ID_PAUSE_FALLBACK = 2

    // Channel importance can't be raised after creation: the LOW channel of the first spike build is replaced.
    private const val OLD_CHANNEL_PROTECTING = "protecting"
    private const val CHANNEL_PROTECTING = "protecting_v2"
    private const val CHANNEL_PAUSE = "safe_pause"

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
        manager.createNotificationChannels(listOf(protecting, pause))
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

    /** Fallback when the background activity start was blocked (no "display over other apps"): heads-up + tap. */
    fun showPauseFallback(context: Context, level: RiskLevel, category: AppCategory, callActive: Boolean) {
        ensureChannels(context)
        val tap = PendingIntent.getActivity(
            context,
            1,
            SafePauseActivity.intent(context, level, category, callActive),
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
            .addAction(
                Notification.Action.Builder(null, context.getString(R.string.pause_ask_child), callChild).build(),
            )
            .setAutoCancel(true)
            .build()
        try {
            manager(context).notify(ID_PAUSE_FALLBACK, notification)
        } catch (e: SecurityException) {
            HcSpikeLog.w("fallback notification refused (POST_NOTIFICATIONS?)", e)
        }
    }
}

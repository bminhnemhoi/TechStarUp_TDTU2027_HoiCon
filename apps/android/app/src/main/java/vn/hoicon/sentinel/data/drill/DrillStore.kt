package vn.hoicon.sentinel.data.drill

import android.content.Context
import vn.hoicon.sentinel.data.remote.DrillOffer
import vn.hoicon.sentinel.data.remote.DrillOffers

/**
 * What the phone remembers about the one drill in play (Spec 028). All of it is fictional script text and ids: no
 * person's data, so plain private preferences are enough (the token is not here).
 */
interface DrillStore {
    /** The offer the person was invited to and has not answered yet, or null. */
    fun pending(): DrillOffer?

    fun savePending(offer: DrillOffer)

    /** The drill the invitation notification was already shown for: it is not shown again every 15 minutes. */
    var notifiedDrillId: String?

    /** The drill the person already answered (or turned down). Its result may still be on its way: do not offer it again. */
    var handledDrillId: String?

    /** The person has answered: forget the script, remember only that this drill is done. */
    fun markHandled(drillId: String)

    /** Reconnecting to another family: nothing of the old one stays. */
    fun clearAll()
}

class PrefsDrillStore(context: Context) : DrillStore {
    private val prefs = context.applicationContext.getSharedPreferences(NAME, Context.MODE_PRIVATE)

    override fun pending(): DrillOffer? = prefs.getString(PENDING, null)?.let(DrillOffers::parse)

    override fun savePending(offer: DrillOffer) {
        prefs.edit().putString(PENDING, offer.json).apply()
    }

    override var notifiedDrillId: String?
        get() = prefs.getString(NOTIFIED, null)
        set(value) = prefs.edit().putString(NOTIFIED, value).apply()

    override var handledDrillId: String?
        get() = prefs.getString(HANDLED, null)
        set(value) = prefs.edit().putString(HANDLED, value).apply()

    override fun markHandled(drillId: String) {
        prefs.edit().remove(PENDING).putString(HANDLED, drillId).apply()
    }

    override fun clearAll() {
        prefs.edit().clear().apply()
    }

    private companion object {
        const val NAME = "hoicon_drill"
        const val PENDING = "pending_offer"
        const val NOTIFIED = "notified_drill_id"
        const val HANDLED = "handled_drill_id"
    }
}

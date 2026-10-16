package vn.hoicon.sentinel

import android.app.Application
import org.junit.Test
import kotlin.test.assertNotNull

/**
 * The default `viewModels()` factory builds an AndroidViewModel by reflection and only finds a constructor that takes
 * exactly the Application. A second parameter, even with a default value, crashes the screen on open (found on the AVD).
 */
class DrillModelFactoryTest {
    @Test
    fun theDefaultFactoryCanBuildTheModels() {
        for (type in listOf(DrillModel::class.java, LookupModel::class.java)) {
            assertNotNull(type.getConstructor(Application::class.java), type.simpleName)
        }
    }
}

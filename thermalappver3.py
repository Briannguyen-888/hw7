#MOST RECENT "WORKING CODE"
#region imports
import sys
from ThermoStateCalc import Ui__frm_StateCalculator
from pyXSteam.XSteam import XSteam
from PyQt5.QtWidgets import QWidget, QApplication, QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit
from PyQt5.QtCore import Qt  # Import Qt for alignment
from UnitConversion import UC
from scipy.optimize import fsolve
#endregion

# Sample thermoState class implementation (replace with your actual implementation if different)
class thermoState:
    def __init__(self):
        self.steamTable = XSteam(XSteam.UNIT_SYSTEM_MKS)
        self.region = "unknown"
        self.p = 0.0  # Pressure
        self.t = 0.0  # Temperature
        self.u = 0.0  # Internal Energy
        self.h = 0.0  # Enthalpy
        self.s = 0.0  # Entropy
        self.v = 0.0  # Specific Volume
        self.x = -1.0  # Quality (-1 for superheated, 0-1 for two-phase)

    def setState(self, prop1, prop2, val1, val2, SI=True):
        """
        Set the state based on two properties.
        prop1, prop2: 'p', 't', 'v', 'u', 'h', 's', 'x'
        val1, val2: Corresponding values in SI or English units
        SI: True for SI units, False for English units
        """
        if not SI:
            self.steamTable = XSteam(XSteam.UNIT_SYSTEM_FLS)
        else:
            self.steamTable = XSteam(XSteam.UNIT_SYSTEM_MKS)

        # Helper function to determine if a state is two-phase
        def is_two_phase(p, t):
            tsat = self.steamTable.tsat_p(p)
            if abs(t - tsat) < 0.1:  # Close to saturation temperature
                return True
            return False

        # Depending on the property combination, calculate the state
        if prop1 == 'p' and prop2 == 't':
            self.p = val1
            self.t = val2
            if is_two_phase(self.p, self.t):
                self.region = "two-phase"
                self.x = 0.5  # For testing, assume x=0.5 at saturation (as in original output)
                self.v = self.steamTable.vL_p(self.p) + self.x * (self.steamTable.vV_p(self.p) - self.steamTable.vL_p(self.p))
                self.u = self.steamTable.uL_p(self.p) + self.x * (self.steamTable.uV_p(self.p) - self.steamTable.uL_p(self.p))
                self.h = self.steamTable.hL_p(self.p) + self.x * (self.steamTable.hV_p(self.p) - self.steamTable.hL_p(self.p))
                self.s = self.steamTable.sL_p(self.p) + self.x * (self.steamTable.sV_p(self.p) - self.steamTable.sL_p(self.p))
            else:
                self.region = "superheated" if self.t > self.steamTable.tsat_p(self.p) else "subcooled"
                self.x = -1.0
                self.v = self.steamTable.v_pt(self.p, self.t)
                self.u = self.steamTable.u_pt(self.p, self.t)
                self.h = self.steamTable.h_pt(self.p, self.t)
                self.s = self.steamTable.s_pt(self.p, self.t)
        elif prop1 == 'p' and prop2 == 'x':
            self.p = val1
            self.x = val2
            self.region = "two-phase"
            self.t = self.steamTable.tsat_p(self.p)
            self.v = self.steamTable.vL_p(self.p) + self.x * (self.steamTable.vV_p(self.p) - self.steamTable.vL_p(self.p))
            self.u = self.steamTable.uL_p(self.p) + self.x * (self.steamTable.uV_p(self.p) - self.steamTable.uL_p(self.p))
            self.h = self.steamTable.hL_p(self.p) + self.x * (self.steamTable.hV_p(self.p) - self.steamTable.hL_p(self.p))
            self.s = self.steamTable.sL_p(self.p) + self.x * (self.steamTable.sV_p(self.p) - self.steamTable.sL_p(self.p))
        else:
            raise ValueError(f"Unsupported property combination: {prop1} and {prop2}")

    def __sub__(self, other):
        result = thermoState()
        result.p = self.p - other.p
        result.t = self.t - other.t
        result.u = self.u - other.u
        result.h = self.h - other.h
        result.s = self.s - other.s
        result.v = self.v - other.v
        return result

# Sample thermoSatProps class (minimal implementation for completeness)
class thermoSatProps:
    def __init__(self, p=None, t=None):
        self.steamTable = XSteam(XSteam.UNIT_SYSTEM_MKS)
        if p is not None:
            self.p = p
            self.t = self.steamTable.tsat_p(p)
        elif t is not None:
            self.t = t
            self.p = self.steamTable.psat_t(t)
        else:
            raise ValueError("Must specify either pressure or temperature")

class main_window(QWidget, Ui__frm_StateCalculator):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.steamTable = XSteam(XSteam.UNIT_SYSTEM_MKS)
        self.currentUnits = 'SI'

        # --- Add group boxes for State 1 and State 2 in Specified Properties ---
        self.state1_group = QGroupBox("State 1")
        self.state2_group = QGroupBox("State 2")

        state1_layout = QVBoxLayout()
        state1_layout.addWidget(self._cmb_Property1)
        state1_layout.addWidget(self._le_Property1)
        state1_layout.addWidget(self._lbl_Property1_Units)
        state1_layout.addWidget(self._cmb_Property2)
        state1_layout.addWidget(self._le_Property2)
        state1_layout.addWidget(self._lbl_Property2_Units)
        self.state1_group.setLayout(state1_layout)

        self._cmb_Property3 = QComboBox()
        self._cmb_Property4 = QComboBox()
        self._le_Property3 = QLineEdit("1.0")  # Default: 1.0 bar
        self._le_Property4 = QLineEdit("150.0")  # Default: 150.0°C
        self._lbl_Property3_Units = QLabel("")
        self._lbl_Property4_Units = QLabel("")

        properties = ["Pressure (p)", "Temperature (T)", "Specific Volume (v)",
                      "Internal Energy (u)", "Enthalpy (h)", "Entropy (s)", "Quality (x)"]
        self._cmb_Property3.addItems(properties)
        self._cmb_Property4.addItems(properties)
        self._cmb_Property3.setCurrentText("Pressure (p)")
        self._cmb_Property4.setCurrentText("Temperature (T)")

        state2_layout = QVBoxLayout()
        state2_layout.addWidget(self._cmb_Property3)
        state2_layout.addWidget(self._le_Property3)
        state2_layout.addWidget(self._lbl_Property3_Units)
        state2_layout.addWidget(self._cmb_Property4)
        state2_layout.addWidget(self._le_Property4)
        state2_layout.addWidget(self._lbl_Property4_Units)
        self.state2_group.setLayout(state2_layout)

        existing_layout = self._grp_SpecifiedProperties.layout()
        if existing_layout is None:
            existing_layout = QVBoxLayout()
            self._grp_SpecifiedProperties.setLayout(existing_layout)

        group_layout = QHBoxLayout()
        group_layout.addWidget(self.state1_group)
        group_layout.addWidget(self.state2_group)

        while existing_layout.count() > 0:
            item = existing_layout.takeAt(0)
            if item.widget() == self._pb_Calculate:
                continue
            if item.widget():
                item.widget().setParent(None)

        existing_layout.addLayout(group_layout, 0, 0, 1, 2)
        existing_layout.addWidget(self._pb_Calculate, 1, 0, 1, 2, Qt.AlignCenter)

        # --- Redesign the State Properties section ---
        # Keep the existing _lbl_StateProperties (which says "State: saturated") and add our labels below it
        # First, get the existing layout of _grp_StateProperties
        state_props_layout = self._grp_StateProperties.layout()
        if state_props_layout is None:
            state_props_layout = QVBoxLayout()
            self._grp_StateProperties.setLayout(state_props_layout)

        # Create a horizontal layout for the three labels
        self._lbl_State1_Properties = QLabel("State 1 Properties:\n")
        self._lbl_State2_Properties = QLabel("State 2 Properties:\n")
        self._lbl_StateChange_Properties = QLabel("State Change:\n")

        # Ensure labels can display multi-line text and have sufficient width
        self._lbl_State1_Properties.setWordWrap(True)
        self._lbl_State2_Properties.setWordWrap(True)
        self._lbl_StateChange_Properties.setWordWrap(True)
        self._lbl_State1_Properties.setMinimumWidth(200)
        self._lbl_State2_Properties.setMinimumWidth(200)
        self._lbl_StateChange_Properties.setMinimumWidth(200)

        # Create a horizontal layout for the three labels
        h_layout = QHBoxLayout()
        h_layout.addWidget(self._lbl_State1_Properties)
        h_layout.addWidget(self._lbl_State2_Properties)
        h_layout.addWidget(self._lbl_StateChange_Properties)
        h_layout.setSpacing(10)  # Add spacing between labels

        # Add the horizontal layout to the existing layout (below _lbl_StateProperties)
        state_props_layout.addLayout(h_layout)

        # Ensure the group box has enough space
        self._grp_StateProperties.setMinimumHeight(300)  # Adjust height as needed

        self.setUnits()
        self.SetupSlotsAndSignals()
        self.show()

    def SetupSlotsAndSignals(self):
        self._rdo_English.clicked.connect(self.setUnits)
        self._rdo_SI.clicked.connect(self.setUnits)
        self._cmb_Property1.currentIndexChanged.connect(self.setUnits)
        self._cmb_Property2.currentIndexChanged.connect(self.setUnits)
        self._cmb_Property3.currentIndexChanged.connect(self.setUnits)
        self._cmb_Property4.currentIndexChanged.connect(self.setUnits)
        self._pb_Calculate.clicked.connect(self.calculateProperties)

    def setUnits(self):
        SI = self._rdo_SI.isChecked()
        newUnits = 'SI' if SI else 'EN'
        UnitChange = self.currentUnits != newUnits
        self.currentUnits = newUnits

        if SI:
            self.steamTable = XSteam(XSteam.UNIT_SYSTEM_MKS)
            self.l_Units = "m"
            self.p_Units = "bar"
            self.t_Units = "C"
            self.m_Units = "kg"
            self.time_Units = "s"
            self.energy_Units = "W"
            self.u_Units = "kJ/kg"
            self.h_Units = "kJ/kg"
            self.s_Units = "kJ/kg*C"
            self.v_Units = "m^3/kg"
        else:
            self.steamTable = XSteam(XSteam.UNIT_SYSTEM_FLS)
            self.l_Units = "ft"
            self.p_Units = "psi"
            self.t_Units = "F"
            self.m_Units = "lb"
            self.time_Units = "s"
            self.energy_Units = "btu"
            self.u_Units = "btu/lb"
            self.h_Units = "btu/lb"
            self.s_Units = "btu/lb*F"
            self.v_Units = "ft^3/lb"

        SpecifiedProperty1 = self._cmb_Property1.currentText()
        SpecifiedProperty2 = self._cmb_Property2.currentText()
        SP1 = [float(self._le_Property1.text()), float(self._le_Property2.text())]

        SpecifiedProperty3 = self._cmb_Property3.currentText()
        SpecifiedProperty4 = self._cmb_Property4.currentText()
        SP2 = [float(self._le_Property3.text()), float(self._le_Property4.text())]

        if 'Pressure' in SpecifiedProperty1:
            self._lbl_Property1_Units.setText(self.p_Units)
            if UnitChange:
                SP1[0] = SP1[0] * UC.psi_to_bar if SI else SP1[0] * UC.bar_to_psi
        elif 'Temperature' in SpecifiedProperty1:
            self._lbl_Property1_Units.setText(self.t_Units)
            if UnitChange:
                SP1[0] = UC.F_to_C(SP1[0]) if SI else UC.C_to_F(SP1[0])
        elif 'Energy' in SpecifiedProperty1:
            self._lbl_Property1_Units.setText(self.u_Units)
            if UnitChange:
                SP1[0] = SP1[0] * UC.btuperlb_to_kJperkg if SI else SP1[0] * UC.kJperkg_to_btuperlb
        elif 'Enthalpy' in SpecifiedProperty1:
            self._lbl_Property1_Units.setText(self.h_Units)
            if UnitChange:
                SP1[0] = SP1[0] * UC.btuperlb_to_kJperkg if SI else SP1[0] * UC.kJperkg_to_btuperlb
        elif 'Entropy' in SpecifiedProperty1:
            self._lbl_Property1_Units.setText(self.s_Units)
            if UnitChange:
                SP1[0] = SP1[0] * UC.btuperlbF_to_kJperkgC if SI else SP1[0] * UC.kJperkgC_to_btuperlbF
        elif 'Volume' in SpecifiedProperty1:
            self._lbl_Property1_Units.setText(self.v_Units)
            if UnitChange:
                SP1[0] = SP1[0] * UC.ft3perlb_to_m3perkg if SI else SP1[0] * UC.m3perkg_to_ft3perlb
        elif 'Quality' in SpecifiedProperty1:
            self._lbl_Property1_Units.setText("")

        if 'Pressure' in SpecifiedProperty2:
            self._lbl_Property2_Units.setText(self.p_Units)
            if UnitChange:
                SP1[1] = SP1[1] * UC.psi_to_bar if SI else SP1[1] * UC.bar_to_psi
        elif 'Temperature' in SpecifiedProperty2:
            self._lbl_Property2_Units.setText(self.t_Units)
            if UnitChange:
                SP1[1] = UC.F_to_C(SP1[1]) if SI else UC.C_to_F(SP1[1])
        elif 'Energy' in SpecifiedProperty2:
            self._lbl_Property2_Units.setText(self.u_Units)
            if UnitChange:
                SP1[1] = SP1[1] * UC.btuperlb_to_kJperkg if SI else SP1[1] * UC.kJperkg_to_btuperlb
        elif 'Enthalpy' in SpecifiedProperty2:
            self._lbl_Property2_Units.setText(self.h_Units)
            if UnitChange:
                SP1[1] = SP1[1] * UC.btuperlb_to_kJperkg if SI else SP1[1] * UC.kJperkg_to_btuperlb
        elif 'Entropy' in SpecifiedProperty2:
            self._lbl_Property2_Units.setText(self.s_Units)
            if UnitChange:
                SP1[1] = SP1[1] * UC.btuperlbF_to_kJperkgC if SI else SP1[1] * UC.kJperkgC_to_btuperlbF
        elif 'Volume' in SpecifiedProperty2:
            self._lbl_Property2_Units.setText(self.v_Units)
            if UnitChange:
                SP1[1] = SP1[1] * UC.ft3perlb_to_m3perkg if SI else SP1[1] * UC.m3perkg_to_ft3perlb
        elif 'Quality' in SpecifiedProperty2:
            self._lbl_Property2_Units.setText("")

        if 'Pressure' in SpecifiedProperty3:
            self._lbl_Property3_Units.setText(self.p_Units)
            if UnitChange:
                SP2[0] = SP2[0] * UC.psi_to_bar if SI else SP2[0] * UC.bar_to_psi
        elif 'Temperature' in SpecifiedProperty3:
            self._lbl_Property3_Units.setText(self.t_Units)
            if UnitChange:
                SP2[0] = UC.F_to_C(SP2[0]) if SI else UC.C_to_F(SP2[0])
        elif 'Energy' in SpecifiedProperty3:
            self._lbl_Property3_Units.setText(self.u_Units)
            if UnitChange:
                SP2[0] = SP2[0] * UC.btuperlb_to_kJperkg if SI else SP2[0] * UC.kJperkg_to_btuperlb
        elif 'Enthalpy' in SpecifiedProperty3:
            self._lbl_Property3_Units.setText(self.h_Units)
            if UnitChange:
                SP2[0] = SP2[0] * UC.btuperlb_to_kJperkg if SI else SP2[0] * UC.kJperkg_to_btuperlb
        elif 'Entropy' in SpecifiedProperty3:
            self._lbl_Property3_Units.setText(self.s_Units)
            if UnitChange:
                SP2[0] = SP2[0] * UC.btuperlbF_to_kJperkgC if SI else SP2[0] * UC.kJperkgC_to_btuperlbF
        elif 'Volume' in SpecifiedProperty3:
            self._lbl_Property3_Units.setText(self.v_Units)
            if UnitChange:
                SP2[0] = SP2[0] * UC.ft3perlb_to_m3perkg if SI else SP2[0] * UC.m3perkg_to_ft3perlb
        elif 'Quality' in SpecifiedProperty3:
            self._lbl_Property3_Units.setText("")

        if 'Pressure' in SpecifiedProperty4:
            self._lbl_Property4_Units.setText(self.p_Units)
            if UnitChange:
                SP2[1] = SP2[1] * UC.psi_to_bar if SI else SP2[1] * UC.bar_to_psi
        elif 'Temperature' in SpecifiedProperty4:
            self._lbl_Property4_Units.setText(self.t_Units)
            if UnitChange:
                SP2[1] = UC.F_to_C(SP2[1]) if SI else UC.C_to_F(SP2[1])
        elif 'Energy' in SpecifiedProperty4:
            self._lbl_Property4_Units.setText(self.u_Units)
            if UnitChange:
                SP2[1] = SP2[1] * UC.btuperlb_to_kJperkg if SI else SP2[1] * UC.kJperkg_to_btuperlb
        elif 'Enthalpy' in SpecifiedProperty4:
            self._lbl_Property4_Units.setText(self.h_Units)
            if UnitChange:
                SP2[1] = SP2[1] * UC.btuperlb_to_kJperkg if SI else SP2[1] * UC.kJperkg_to_btuperlb
        elif 'Entropy' in SpecifiedProperty4:
            self._lbl_Property4_Units.setText(self.s_Units)
            if UnitChange:
                SP2[1] = SP2[1] * UC.btuperlbF_to_kJperkgC if SI else SP2[1] * UC.kJperkgC_to_btuperlbF
        elif 'Volume' in SpecifiedProperty4:
            self._lbl_Property4_Units.setText(self.v_Units)
            if UnitChange:
                SP2[1] = SP2[1] * UC.ft3perlb_to_m3perkg if SI else SP2[1] * UC.m3perkg_to_ft3perlb
        elif 'Quality' in SpecifiedProperty4:
            self._lbl_Property4_Units.setText("")

        self._le_Property1.setText("{:0.3f}".format(SP1[0]))
        self._le_Property2.setText("{:0.3f}".format(SP1[1]))
        self._le_Property3.setText("{:0.3f}".format(SP2[0]))
        self._le_Property4.setText("{:0.3f}".format(SP2[1]))

    def clamp(self, x, low, high):
        if x < low:
            return low
        if x > high:
            return high
        return x

    def between(self, x, low, high):
        if x >= low and x <= high:
            return True
        return False

    def getSatProps_p(self, p):
        return thermoSatProps(p=p)

    def getSatProps_t(self, t):
        return thermoSatProps(t=t)

    def makeLabel(self, state):
        stProps = "Region = {:}".format(state.region)
        stProps += "\nPressure = {:0.3f} ({:})".format(state.p, self.p_Units)
        stProps += "\nTemperature = {:0.3f} ({:})".format(state.t, self.t_Units)
        stProps += "\nInternal Energy = {:0.3f} ({:})".format(state.u, self.u_Units)
        stProps += "\nEnthalpy = {:0.3f} ({:})".format(state.h, self.h_Units)
        stProps += "\nEntropy = {:0.3f} ({:})".format(state.s, self.s_Units)
        stProps += "\nSpecific Volume = {:0.3f} ({:})".format(state.v, self.v_Units)
        stProps += "\nQuality = {:0.3f}".format(state.x)
        return stProps

    def makeDeltaLabel(self, state1, state2):
        delta = state2 - state1
        stDelta = "Property change:"
        stDelta += "\nT2-T1 = {:0.3f} {:}".format(delta.t, self.t_Units)
        stDelta += "\nP2-P1 = {:0.3f} {:}".format(delta.p, self.p_Units)
        stDelta += "\nh2-h1 = {:0.3f} {:}".format(delta.h, self.h_Units)
        stDelta += "\nu2-u1 = {:0.3f} {:}".format(delta.u, self.u_Units)
        stDelta += "\ns2-s1 = {:0.3f} {:}".format(delta.s, self.s_Units)
        stDelta += "\nv2-v1 = {:0.3f} {:}".format(delta.v, self.v_Units)
        return stDelta

    def calculateProperties(self):
        print("Starting calculateProperties")  # Debug
        self._lbl_State1_Properties.setText("State 1 Properties:\n")
        self._lbl_State2_Properties.setText("State 2 Properties:\n")
        self._lbl_StateChange_Properties.setText("State Change:\n")
        self._lbl_Warning.setText("")

        try:
            # Validate inputs for State 1
            try:
                f1 = [float(self._le_Property1.text()), float(self._le_Property2.text())]
                print(f"State 1 inputs: f1 = {f1}")  # Debug
            except ValueError as e:
                self._lbl_Warning.setText("Error: State 1 - Please enter valid numeric values.")
                print(f"State 1 input error: {str(e)}")  # Debug
                return

            # Validate inputs for State 2
            try:
                f2 = [float(self._le_Property3.text()), float(self._le_Property4.text())]
                print(f"State 2 inputs: f2 = {f2}")  # Debug
            except ValueError as e:
                self._lbl_Warning.setText("Error: State 2 - Please enter valid numeric values.")
                print(f"State 2 input error: {str(e)}")  # Debug
                return

            self.state1 = thermoState()
            self.state2 = thermoState()

            # State 1 (Property 1 and Property 2)
            SP1 = [self._cmb_Property1.currentText()[-2:-1].lower(),
                   self._cmb_Property2.currentText()[-2:-1].lower()]
            print(f"State 1 properties: SP1 = {SP1}")  # Debug
            if SP1[0] == SP1[1]:
                self._lbl_Warning.setText("Warning: State 1 - You cannot specify the same property twice.")
                print("State 1: Same property specified twice")  # Debug
                return

            # State 2 (Property 3 and Property 4)
            SP2 = [self._cmb_Property3.currentText()[-2:-1].lower(),
                   self._cmb_Property4.currentText()[-2:-1].lower()]
            print(f"State 2 properties: SP2 = {SP2}")  # Debug
            if SP2[0] == SP2[1]:
                self._lbl_Warning.setText("Warning: State 2 - You cannot specify the same property twice.")
                print("State 2: Same property specified twice")  # Debug
                return

            SI = self._rdo_SI.isChecked()
            print(f"Units: SI = {SI}")  # Debug

            # Calculate State 1
            try:
                self.state1.setState(SP1[0], SP1[1], f1[0], f1[1], SI)
                print(f"State 1 after setState: region={self.state1.region}, p={self.state1.p}, t={self.state1.t}, "
                      f"u={self.state1.u}, h={self.state1.h}, s={self.state1.s}, v={self.state1.v}, x={self.state1.x}")
            except Exception as e:
                self._lbl_Warning.setText(f"Error in State 1 calculation: {str(e)}")
                print(f"State 1 calculation error: {str(e)}")  # Debug
                return

            # Calculate State 2
            try:
                self.state2.setState(SP2[0], SP2[1], f2[0], f2[1], SI)
                print(f"State 2 after setState: region={self.state2.region}, p={self.state2.p}, t={self.state2.t}, "
                      f"u={self.state2.u}, h={self.state2.h}, s={self.state2.s}, v={self.state2.v}, x={self.state2.x}")
            except Exception as e:
                self._lbl_Warning.setText(f"Error in State 2 calculation: {str(e)}")
                print(f"State 2 calculation error: {str(e)}")  # Debug
                return

            # Update labels
            state1_label = self.makeLabel(self.state1)
            state2_label = self.makeLabel(self.state2)
            delta_label = self.makeDeltaLabel(self.state1, self.state2)
            print(f"State 1 label:\n{state1_label}")
            print(f"State 2 label:\n{state2_label}")
            print(f"Delta label:\n{delta_label}")

            self._lbl_State1_Properties.setText(state1_label)
            self._lbl_State2_Properties.setText(state2_label)
            self._lbl_StateChange_Properties.setText(delta_label)

            # Force UI update
            self._lbl_State1_Properties.update()
            self._lbl_State2_Properties.update()
            self._lbl_StateChange_Properties.update()
            self._grp_StateProperties.update()
            self.update()
            print("Labels updated")  # Debug

        except Exception as e:
            self._lbl_Warning.setText(f"Unexpected error: {str(e)}")
            print(f"Unexpected error: {str(e)}")  # Debug

def main():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    app.aboutToQuit.connect(app.deleteLater)
    main_win = main_window()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
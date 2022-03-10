# Phases
class Phases:
    powering_on = "powering_on"
    powering_off = "powering_off"
    configuring = "configuring"
    none = ""

# Actions
class Actions:
    power_on = "powering_on"
    power_off_gracefully = "powering_off_gracefully"
    power_off_forcefully = "powering_off_forcefully"
    session_setup = "session_setup"

# Status
class Status:
    power_on_pending
    power_on_called
    power_off_pending
    power_off_gracefully_called
    power_off_forcefully_called
    configuring
    stable
    failed
    on_hold # TODO
# saptune - Configures saptune

## Synopsis

The module will configure <code>saptune</code>\. It handles applying Notes and Solution\, configuring <code>saptune\.service</code>\, disabling <code>tuned\.service</code> and <code>sapconf\.service</code> and enabling/disabling of staging\. <b>Keep in mind\, that the system might not tuned correctly or tuned at all during it makes changes and that a failure can leave the system in a badly tuned state\. Do not change the tuning on a system with SAP software currently running\!</b>


## Requirements

The below requirements are needed on the host that executes this module.

- <code>saptune</code> must support JSON output \(\>\= 3\.1\)

## Parameters

| Parameter     | Defaults/Choices  | Comments |
| ------------- | ----------------- |--------- |
| `apply`<br />list / optional |  []    |  List of Notes or a Solution which shall be applied in this order. No optimization is done to remove unnecessary applies or reverts. Only one Solution is allowed and must start with C(@). Notes can be prefixed by C(-) to revert it. If O(apply) is missing, the tuning will be left alone. An empty O(apply) means, that no tuning shall be applied.  |
| `force_reapply`<br />bool / optional |  False    |  Defines if the tuning will be re-applied even if it is already in the requested state.  |
| `no_tuned`<br />bool / optional |  True    |  Defines if C(tuned.service) should be stopped and disabled.  |
| `no_sapconf`<br />bool / optional |  True    |  Defines if C(sapconf.service) should be stopped and disabled.  |
| `enabled`<br />bool / optional |  True    |  Defines if C(saptune.service) shall be started. Remember, that C(sapconf) conflicts with C(saptune), so put it out of the way by yourself or set O(no_sapconf) to true.  |
| `started`<br />bool / optional |  True    |  Defines if C(saptune.service) shall be enabled. Remember, that C(sapconf) conflicts with `saptune`, so put it out of the way by yourself or set O(no_sapconf) to true.  |
| `keep_applied_if_stopped`<br />bool / optional |  False    |  Defines if the tuning shall remain active even if `saptune.service` was set to be stopped.  |
| `ignore_non_compliant`<br />bool / optional |  False    |  Defines if a non-compliant tuning will be ignored. If set to false, a non-compliant tuning will result in an error. In case the tuning is already in the desired state (nothing in regards of tuning would be done) a re-apply will be triggered. If this is not wanted, set this parameter to true.  |
| `ignore_degraded`<br />bool / optional |  True    |  A degraded systemd system state will result in an error. If this is not wanted, set this parameter to true.  |
| `staging_enabled`<br />bool / optional |  False    |  Defines state of staging.  |

## Examples

```yaml
    
    # Tune for SAP HANA
    - name: Tune for SAP HANA
      saptune:
        apply:
          - '@HANA'

    # Just make sure, the service is running and enabled
    - name: saptune.service shall be active and enabled
      saptune:
        enabled: true
        started: true

    # Make sure staging is enabled
    - name: Set HANA solution
      saptune:
        staging_enabled: true

```

## Return Values

 	 	
| Key     | Returned  | Description |
| ------- | --------- |------------ |
| `commands`<br />list | success |  List of commands, which are executed to get to the desired state. <br /><br />Sample: `["saptune revert all"]` |
| `saptune_status`<br />dict | always |  The result object of the last C(saptune --format json status) executed by the module. <br /><br />Sample: `{ "services": { "saptune": [ "enabled", "active" ], "sapconf": [], "tuned": [] }, "systemd system state": "running", "tuning state": "compliant", "virtualization": "oracle", "configured version": "3", "package version": "3.1.3", "Solution enabled": [], "Notes enabled by Solution": [], "Solution applied": [], "Notes applied by Solution": [], "Notes enabled additionally": [ "SAP_BOBJ" ], "Notes enabled": [ "SAP_BOBJ" ], "Notes applied": [ "SAP_BOBJ" ], "staging": { "staging enabled": false, "Notes staged": [], "Solutions staged": [] }` |



## Authors

- Sören Schmidt (soeren.schmidt@suse.com)

# saptune_facts - Get saptune status as fact

## Synopsis

The module will make the result of <code>saptune \-\-format json status</code> available as Ansible fact\.


## Requirements

The below requirements are needed on the host that executes this module.

- <code>saptune</code> must support JSON output \(\>\= 3\.1\)

## Parameters

| Parameter     | Defaults/Choices  | Comments |
| ------------- | ----------------- |--------- |
| `compliance_check`<br />bool / optional |  True    |  Defines if a compliance check shall be done.  |

## Examples

```yaml
    
    # Simply get the facts
    - name: Tune for SAP HANA
      saptune_facts:

    # Get the facts, but skip compliance check
    - name: Tune for SAP HANA
      saptune_facts:
        compliance_check: false


```

## Return Values

 	 	
| Key     | Returned  | Description |
| ------- | --------- |------------ |
| `saptune`<br />dict | always |  The result object of the last C(saptune --format json status). <br /><br />Sample: `{ "services": { "saptune": [ "enabled", "active" ], "sapconf": [], "tuned": [] }, "systemd system state": "running", "tuning state": "compliant", "virtualization": "oracle", "configured version": "3", "package version": "3.1.3", "Solution enabled": [], "Notes enabled by Solution": [], "Solution applied": [], "Notes applied by Solution": [], "Notes enabled additionally": [ "SAP_BOBJ" ], "Notes enabled": [ "SAP_BOBJ" ], "Notes applied": [ "SAP_BOBJ" ], "staging": { "staging enabled": false, "Notes staged": [], "Solutions staged": [] }` |



## Authors

- Sören Schmidt (soeren.schmidt@suse.com)

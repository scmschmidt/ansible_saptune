# How the Modules Work in Detail

## `saptune`

The module always changes the system only in case the configuration of the host differs from the configuration described in the task. 



The first step is calling `saptune status` to get an overview about tuning and state of `systemd` services.

Afterwards staging is verified and depending on the current and the desired state the appropriate command (`saptune staging enable`/`saptune staging disable`) will be added to the command list.

Next the commands to stop and disable `tuned.service` (`systemctl stop tuned.service`) as well as `sapconf.service` (`systemctl stop sapconf.service`) are added to the command list depending `no_tuned` and `no_sapconf` are set to true.

Next the commands to get `saptune.service` enabled or disabled is added to the command list and
afterwards also the commands to stop it, but only if `keep_applied_if_stopped` is set to true.
Stopping `saptune` has to be done before any tuning in that case, to keep the tuning even the service has been stopped.

Now it is time to generate the commands to tune accordingly to the apply list. 
This only needs to be done if the apply list is present in the configuration. If it is missing, the user wants to keep the tuning untouched. 

To generate the commands... ((TBD))

With active tuning in mind the 


Takes the apply list and calculates the effective Notes
    (how "applied Notes" should look like) and the effective
    Solution (what "applied Solution" should list) as well as
    the commands to achieve it.
    
    If the calculated Notes and Solution does not differ
    from the current ones and the system is compliant and we shall
    check for it, an empty command list is returned.
    
    If there is a difference, a non-comliance we should consider
    or `force_reapply` is set, the calculated commands are returned,
    starting with a `saptune revert all`.

    In case of an error module.fail_json() gets called.
    
    Important:
    No optimizations are done to remove unnecessary applies or reverts.
    Some users may create "interesting" apply lists, but adding complex
    code to mimic saptune behavior for such rare events is too risky. 
    It can introduce bugs and requires adaptation if saptune changes 
    its behavior. In the worst case a version switch might become necessary.
       
    Nevertheless we track Note apply and removal to calculate the 
    effective Note list as well we check if all Notes of a Solution
    have been removed to reset the effective Solution. Saptune will
    do the same."""










Next we add the commands to start or stop `saptune.service` to the command list. if not done already due to `keep_applied_if_stopped`.

If check mode is set to true, the module returns now, otherweise all the commands in the command list are getting executed. A final `saptune status` is called to check if the current list of applied Notes and the applied Solution really matches the apply list and, depending on `ignore_non_compliant` and `ignore_degraded`, the tuning is compliant and the `systemd` system state is not degraded.

Finally th module returns. All executed commands in regard to configure the system can be found in `commands`. `stdout`, `stdout_lines`, `stderr` und `stderr_lines` contain the output of those commands. The final `saptune` status is available in `saptune_status` in JSON.


## `saptune_facts`
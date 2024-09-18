# How the Modules Work in Detail

## `saptune`

The first step is calling `saptune status` to get an overview about tuning and state of `systemd` services.

Afterwards staging is verified and depending on the current and the desired state the appropriate command (`saptune staging enable`/`saptune staging disable`) will be added to the command list.

Next the commands to stop and disable `tuned.service` (`systemctl stop tuned.service`) as well as `sapconf.service` (`systemctl stop sapconf.service`) are added to the command list depending `no_tuned` and `no_sapconf` are set to true.

Next the commands to get `saptune.service` enabled or disabled is added to the command list and
afterwards also the commands to stop it, but only if `keep_applied_if_stopped` is set to true.
Stopping `saptune` has to be done before any tuning in that case, to keep the tuning even the service has been stopped.

Now it is time to generate the commands to tune accordingly to the apply list. 
This only needs to be done if the apply list is present in the configuration. If it is missing, the user wants to keep the tuning untouched and the step is skipped. 

The command list starts always with `saptune revert all`.
For each entry of the apply list:

- Check if a Solution has an unsupported `-` operator and throw an error if that is case.

- Check if it is present in the list of known Solutions (`saptune solution   list`) or Notes (`saptune note list`) on that host. If not, throw an error.

- In case of a Solution save that one as the effective Solution and add its Notes to the effective Note list. If a Solution already has been processed, throw an error. Only one Solution is allowed.
A `saptune solution apply SOLUTION` gets added to the command list. 

- In case of a Note either append the Note to the effective Note list and a `saptune note apply NOTE` to the command list or remove the Note from the effective Note list and add a `saptune note revert NOTE` to the command list, depending on the operator.

- One behavior of saptune has to taken into consideration. If all Notes of an applied Solution have been reverted, `saptune` will consider the Solution as not applied anymore. If this is the case when processing the apply list, we also remove the effective Solution. 

We have now the list of effective Notes, the effective Solution as well as all tuning commands. There are a few cases when the command list has to be emptied:

- `force_reapply` is set to `false` and no tuning is required (apply list is empty) and also no tuning is active (no applied Notes).

- `force_reapply` is set to `false` and the tuning of the system is already matching the one from the apply list (the list of effective Notes is matching the list of applied Notes on the system). 
In case of a non-compliant system and `ignore_non_compliant` set to true, this is skipped and the command list is not emptied.


> :warning: The apply list will not be cleaned or optimized any further to reduce redundant applies or remove applies and reverts which cancel each out. Under the assumption, that the apply list was created to honestly tune a system and not to do "weird stuff", such optimizations would cause complex code prone to have bugs. Also each change in `saptune` internals would cause changes in the module and most certainly introduce version switches. With `saptune` itself be able to handle such thing, optimizations have been rejected.

> :warning: Comparison will only be done with the applied Solution and the applied Notes, but **not** the configured ones. The module takes care of the active tuning only. By default `saptune` will mark applied Notes and Solutions as enabled as well. 

> There is a situation when an unnecessary tuning will take place! The apply list matches the list of enabled Notes and the enabled Solution, but `saptune` has not been started yet, so the applied Notes and the applied Solution is empty. Currently the module does not detect that and executes the commands to apply the configured Notes and Solution. Depending on the value of `started`, the entire action was unnecessary, because we end up with the same state the system was before (`saptune` shall kept stopped) or a simple start of `saptune.service` would have been sufficient (`saptune` shall be started). If requested, this will be covered later.

Next we add the commands to start or stop `saptune.service` to the command list. if not done already due to `keep_applied_if_stopped`.

If check mode is set to true, the module returns now, otherweise all the commands in the command list are getting executed. A final `saptune status` is called to check if the current list of applied Notes and the applied Solution really matches the apply list and, depending on `ignore_non_compliant` and `ignore_degraded`, the tuning is compliant and the `systemd` system state is not degraded.

Finally th module returns. All executed commands in regard to configure the system can be found in `commands`. `stdout`, `stdout_lines`, `stderr` und `stderr_lines` contain the output of those commands. The final `saptune` status is available in `saptune_status` in JSON.


## `saptune_facts`

This module is fairly simple and makes the result object of `saptune --format json status` available in the Ansible facts in `saptune`.
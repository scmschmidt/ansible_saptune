# ansible_saptune

**Currently in alpha state! It seems to work but has not yet tested fully.**

Contains two modules:

- `saptune` to configure `saptune` and 
- `saptune_facts` to get the `saptune` status in Ansible facts.

# Installation 

Put the content of the `library/` or the directory itself in a appropriate place. See: https://docs.ansible.com/ansible/latest/dev_guide/developing_locally.html#adding-a-module-or-plugin-outside-of-a-collection


# Usage

See [saptune.md](docs/saptune.md) and [saptune_facts.md](docs/saptune_facts.md) for more details about how to use the modules.

## Todo

- Add diff mode support
- Handle some corner cases to avoid unnecessary steps.  
- Add features if requested.
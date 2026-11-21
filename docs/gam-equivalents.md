# GAM equivalents for the Workspace mock

`GoogleWorkspaceMock` does not run GAM and does not hold a service account. The methods line up with these commands if you later point the same steps at a domain you control.

| Mock method | GAM command |
|---|---|
| `ensure_user` | `gam create user <email> firstname <first> lastname <last>` |
| `update_user` | `gam update user <email> organization department "<department>" organization title "<title>"` |
| `suspend_user` | `gam update user <email> suspended on` |
| `transfer_drive` | `gam user <email> transfer drive <manager>` |
| `add_to_group` | `gam update group <group> add member user <email>` |
| `remove_all_groups` | `gam update group <group> remove member <email>` for each group |

The leaver runs suspend and the drive transfer only after the approval is complete. The mock records `drive_status=transferred` and does not copy files.

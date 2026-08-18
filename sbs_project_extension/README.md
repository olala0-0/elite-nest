# SBS Project Extension

SBS Project Extension provides dedicated areas in Odoo Project for recording
operational, client, technical, review, team, AMC, credential, and financial
information in one place.

## Features

- Adds structured summary and project-information fields.
- Records functional analysts, developers, project managers, and engagement details.
- Maintains client, technical, production, staging, and AMC information.
- Tracks project and customer review sessions.
- Manages financial collection plans and collection history.
- Provides dedicated list, form, search, and configuration views.
- Separates general, credential, and financial access through dedicated groups.
- Stores credential and financial values in project-linked detail records with
  dedicated model access while preserving the existing project field names.
- Allows only Odoo Administrators to lock or unlock projects.
- Prevents all project and linked-detail changes while a project is locked.
- Orders projects by a user-maintained priority number in kanban and list views.
- Supports Project Directors, Project Coordinators, and Internal or Hybrid teams.
- Provides an independent **Read Task Only** group that can view and create
  accessible tasks without editing or deleting them.
- Limits task deletion and manual project creation/deletion to
  **SBS Project Admin** users.
- Provides a per-task work timer that counts time and logs it to the task
  timesheet through a confirmation wizard.
- Allows the counted time to be reduced before it is logged, never increased.
- Restricts editing and deleting task timesheets to **SBS Project Admin** users.

## Task work timer

The timer requires **Timesheets** (`hr_timesheet`) and is available to any user
with Timesheets access. Both **SBS Project User** and **Read Task Only** include
that access.

Open a task and use the buttons in the header:

1. **Start** begins counting. One timer may run at a time per user, and the
   project must have Timesheets enabled.
2. **End** stops the count and opens the log wizard.
3. In the wizard, set the date and description, optionally reduce the time, then
   select **Add to Timesheet**. **Keep for Later** leaves the counted time
   pending, and **Discard Timer** deletes it without logging.

The counted time is always taken from the timer itself, so the time written to
the timesheet can never exceed the time actually counted. A pending count stays
on the task until it is logged or discarded, and the task shows **Log Time**
until then.

Once time reaches the timesheet, only an SBS Project Admin can edit or delete
that timesheet line. Ordinary Odoo timesheet entry is unchanged, so users may
still record time that was never timed.

## Configuration

Assign access according to responsibility:

- **SBS Project Extension** provides the general extended project pages.
- **SBS Project Password User** additionally provides the Credentials page and list.
- **SBS Project Financial User** additionally provides the Financials page and list.
- **SBS Project Admin** provides full SBS project access and is required for
  manual project creation, project deletion, and task deletion.
- **Read Task Only** is an independent task-access selection. It may be assigned
  together with any SBS Project Role and preserves standard project follower
  and privacy rules.

The password and financial groups automatically include the general SBS Project
Extension access. Select the combined Credentials & Financial role when both
specialized access sets are required.

Credential and financial users maintain their protected values through the
dedicated Credentials and Financials menus. Existing field names on projects
remain available for compatibility. Credential values remain deliberately
visible to authorized credential users.

## User documentation

See the [SBS Project Extension User Manual](doc/USER_MANUAL.md) for role setup,
project and task workflows, team formation, review sessions, credentials,
financials, locking, and troubleshooting.

## Company

[Star Bit Solutions](https://starbitsolutions.com/)

## License

Affero General Public License v3.0 (AGPL v3).

## Contact

- Email: info@starbitsolutions.com
- Website: https://starbitsolutions.com

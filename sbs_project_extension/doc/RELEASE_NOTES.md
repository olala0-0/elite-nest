## Module <sbs_project_extension>

#### 15.08.2026
#### Version 19.0.3.0.0
##### ADD
- Added a per-task work timer with Start, End, and Log Time controls on the task form
- Added a log wizard that writes the counted time to the task timesheet with a date and description
- Added an HH:MM:SS duration widget and a live running-timer display

##### CHANGE
- Added Timesheets (`hr_timesheet`) as a module dependency
- SBS Project User and Read Task Only now include Timesheets access, which is granted to existing users of those roles on upgrade
- Restricted editing and deleting task timesheets to SBS Project Admins, and marked those lines read-only in the task Timesheets tab so the restriction is visible before it is enforced
- Timers are now read-only for ordinary users; only SBS Project Admins can modify or remove a timer record

- Timesheet entry outside the timer is unchanged; only the correction of an existing task timesheet is restricted
- Added a translation template and browser tests for the timer widgets

##### FIX
- The time written to a timesheet is now measured from the timer itself, so a wizard submitted outside the normal flow can no longer log more time than was counted
- The logged task is now taken from the timer, so counted time cannot be redirected to another task
- A counted time can no longer be attached to, read from, or discarded through another user's timer
- Adding a timesheet line from the task Timesheets tab is no longer blocked for ordinary users
- Unchecking Billable on a project no longer fails for users who are not SBS Project Admins
- Logging now works for users whose active company differs from the company of their employee record
- Stopping a timer in the same second it started removes it and reports that nothing was counted, instead of failing and leaving the timer running
- Time to Log now accepts a plain decimal such as 0.75 in addition to HH:MM:SS
- Rejected timers whose stop time precedes their start time
- Enforced one running timer per user with a database index rather than a check that could be raced
- The running-timer badge now counts from the time measured by the server, so a workstation whose clock is wrong no longer shows a shifted or zeroed elapsed time
- Project Summary and Project Master no longer fail to open for users without the SBS Project User role; the risk colour now marks the Risk Level cell instead of the whole row, because the row colour forced every reader to have access to the restricted Risk Level field

#### 11.08.2026
#### Version 19.0.2.0.0
##### ADD
- Added an independent Read Task Only role with view and create access but no task editing
- Added project priority ordering, Project Director, Project Coordinators, and team formation types
- Added internal-user-backed project team entries while preserving manual hybrid team entries

##### CHANGE
- Limited task deletion and manual project creation/deletion to SBS Project Admins
- Preserved trusted server-side project generation through sudo
- Moved credentials and financial values to access-controlled project-linked detail models
- Made financial amounts currency-aware and required projects on collection records
- Restricted general SBS project fields at ORM level
- Applied project priority ordering to standard and SBS project views
- Moved Project Master after Tasks

##### FIX
- Prevented access to review sessions containing inaccessible projects

#### 10.08.2026
#### Version 19.0.1.3.1
##### FIX
- Limited project Lock and Unlock controls to Odoo Administrators
- Prevented all users, including administrators, from changing locked projects and their linked details until they are unlocked

#### 17.07.2026
#### Version 19.0.1.2.0
##### FIX
- Collection and review lines now follow the linked project's company and privacy access rules
- Prevented direct access to project details when the linked project is inaccessible

#### 17.07.2026
#### Version 19.0.1.1.0
##### ADD
- Added independent password and financial user groups
- Restricted credential and financial fields, form pages, lists, and menus to their respective groups

#### 16.07.2026
#### Version 19.0.1.0.0
##### ADD
- Initial Odoo 19 release of SBS Project Extension
- Star Bit Solutions branding and Odoo Apps Store documentation

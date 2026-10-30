# SBS Project Extension User Manual

## Document information

| Item | Value |
|---|---|
| Module | SBS Project Extension (`sbs_project_extension`) |
| Module version | 19.0.3.0.0 |
| Platform | Odoo 19 |
| Primary application | Project |
| Intended audience | Project administrators, project teams, reviewers, credential users, and financial users |

This manual explains how to configure and use the SBS Project Extension. It
also explains which operations are intentionally restricted.

## 1. What the module adds

The module extends Odoo Project with:

- project priority and Project Director fields;
- project summary, risk, client, technical, AMC, and team information;
- Internal and Hybrid project teams;
- Project Coordinators;
- project review sessions and review history;
- separate credential and financial access;
- collection plans and collection history;
- project locking;
- an independent Read Task Only role;
- a per-task work timer that logs counted time to the task timesheet;
- administrator-only editing and deletion of task timesheets;
- administrator-only task deletion; and
- administrator-only manual project creation and deletion.

The normal Odoo project visibility rules still apply. A role provided by this
module does not let a user bypass company, privacy, follower, or other standard
Odoo record rules.

## 2. Access roles

Open **Settings > Users & Companies > Users**, select a user, and open the
**Access Rights** tab. The module provides two independent selections under
the **SBS Project Extension** category:

1. **SBS Project Role** controls extended project information.
2. **SBS Task Access** optionally applies the Read Task Only restriction.

### 2.1 SBS Project Role

Select one SBS Project Role per user.

| Role | General SBS information | Credentials | Financials | Manually create/delete projects | Delete tasks |
|---|---:|---:|---:|---:|---:|
| SBS Project User | Yes | No | No | No | No |
| SBS Project Credentials User | Yes | Yes | No | No | No |
| SBS Project Financial User | Yes | No | Yes | No | No |
| SBS Project Credentials & Financial User | Yes | Yes | Yes | No | No |
| SBS Project Admin | Yes | Yes | Yes | Yes | Yes |

The Credentials and Financial roles automatically include general SBS Project
access. To grant both specialized access sets, select **SBS Project
Credentials & Financial User**; do not assign separate SBS Project roles.

### 2.2 Read Task Only

**Read Task Only** is independent of the SBS Project Role and can be assigned
with any SBS Project Role.

A Read Task Only user can:

- view tasks that standard Odoo access rules make visible;
- create tasks in accessible projects;
- add comments;
- add followers;
- schedule activities; and
- record timesheets when the Timesheets application is installed and the user
  has the normal Timesheets access right.

A Read Task Only user cannot:

- edit an existing task;
- move a task to another stage by editing or dragging it; or
- delete a task.

For a follower-only project, add the user as a project follower before the user
tries to view or create tasks. This module does not broaden that standard Odoo
rule.

### 2.3 Special administrator boundaries

- Only an **SBS Project Admin** can manually create or delete a project.
- Only an **SBS Project Admin** can delete a task.
- Standard users retain their normal task creation and editing behavior unless
  Read Task Only is assigned.
- Trusted server-side automation running with Odoo `sudo` may create projects.
  This preserves standard automated workflows such as sale-service project
  generation. An ordinary UI, import, or API request does not receive this
  bypass.
- The **Lock** and **Unlock** buttons require Odoo's Administration/Settings
  access. SBS Project Admin by itself does not grant those buttons.

## 3. Initial configuration

Before creating projects, prepare the reusable values under:

**Project > Configuration > SBS Project Settings**

Available menus are:

- **Risk Factor Settings** — values used by the Risk Factor field;
- **Industry Vertical Settings** — values used by Industry;
- **Tech Stack Settings** — values used by Tech Stack; and
- **Project Team Settings** — manually maintained team names used by Hybrid
  projects.

Internal Odoo users are automatically synchronized into Project Team Settings.
These synchronized entries are linked to their users and cannot be manually
renamed or deleted. User name and active-status changes are synchronized from
the user account.

Manually created Project Team entries are retained for Hybrid teams. They are
not considered internal users, even if their name matches an Odoo user.

## 4. Project Master navigation

In the Project application, **Project Master** appears immediately after
**Tasks**. It contains:

| Menu | Purpose |
|---|---|
| Project Summary | Compact operational and risk overview |
| Project Master | Detailed cross-project list |
| Review | Create and maintain project review sessions |
| Team Engagement | Compare team assignments across projects |
| Client and Technical | Review client and technical information |
| AMC | Review AMC status and dates |
| Credentials | Maintain credential records; visible only to credential roles |
| Financials | Maintain financial records; visible only to financial roles |

The standard Projects kanban/list and the SBS project lists are ordered by
**Priority Number**.

## 5. Creating a project

Only an SBS Project Admin can perform these steps:

1. Open **Project > Projects**.
2. Select **New**.
3. Enter the project name and normal Odoo project information.
4. Enter **Priority Number**.
5. Select the **Project Director**.
6. Select the **Project Manager**.
7. Complete the relevant SBS tabs described below.
8. Save the project.

### 5.1 Priority Number

- Use a positive whole number for prioritized projects.
- Lower positive numbers appear first.
- `0` means unprioritized and appears after positive priorities.
- Negative priorities are not accepted.
- Priority is evaluated before the normal favorite and sequence ordering in the
  standard project kanban and list views.

### 5.2 Project Director and Project Manager

**Project Director** appears above **Project Manager** in both the full and
simplified project creation forms. Both fields select from internal Odoo users.

## 6. Project form tabs

### 6.1 Summary

Use the Summary tab to maintain:

- Risk Level: Low, Medium, or High;
- Risk Factor;
- Delivery Type: AMC, Development, or Payment Pending;
- Next Action; and
- Additional Notes.

High- and medium-risk projects are visually decorated in the Project Summary
and Project Master lists.

### 6.2 Review History

This tab is read-only and shows review entries recorded through Project Review
sessions. It includes internal and customer review information, timelines,
completion percentages, task-frozen indicators, remarks, and next actions.

### 6.3 Team

First select **Team Formation Type**:

- **Internal** — team fields accept only entries backed by internal Odoo users.
- **Hybrid** — team fields accept both synchronized internal users and manually
  maintained Project Team entries.

Available assignments are:

- Sales Person;
- Project Managers;
- Developers;
- QA;
- Functional Consultant;
- Project Coordinators;
- Key Accounts Manager; and
- Client Success Manager.

When changing a Hybrid project to Internal, remove every manually maintained
team entry first. Odoo blocks the change and lists the external entries if any
remain.

Team values cannot be created from the project field itself. Create reusable
manual entries under **Project > Configuration > SBS Project Settings > Project
Team Settings**, then return to the project. Internal-user entries are created
automatically.

### 6.4 Client Details

Maintain:

- Industry;
- client name, country, website, and address;
- SPOC name, designation, phone, email, and CC email; and
- WhatsApp group name.

### 6.5 Technical Info

Maintain:

- Git repository link;
- repository creator;
- Git privacy: Public or Private;
- Tech Stack; and
- cloud-storage link.

### 6.6 AMC Details

Maintain:

- AMC Status: Active, Expired, Development, or Inactive;
- free AMC start and expiry dates;
- paid AMC start and expiry dates; and
- remarks.

### 6.7 Credentials

This tab is visible only to credential-authorized users. It stores production
and staging values for:

- hosting;
- application link;
- database name;
- database user and password;
- master password;
- server IP;
- SSH user and password; and
- server operating system.

Credential values are intentionally visible text fields; they are not masked
or encrypted by this module. Grant the credential role only to users who are
authorized to see these values.

Each project has one dedicated credential record. Authorized users can also
open **Project > Project Master > Credentials** to search and edit these
records. Credential records cannot be manually created or deleted from that
menu.

The user must also be able to read the related project. Credential access alone
does not reveal credentials for an inaccessible project.

### 6.8 Financials

This tab is visible only to financial-authorized users.

The main values are:

- Proposed Value;
- Locked Value; and
- Revised Value.

Amounts use the project's company currency. Each project has one dedicated
financial record. Authorized users can also open **Project > Project Master >
Financials** to search and edit the main values. Financial records cannot be
manually created or deleted from that menu.

#### Collection Plan

Add planned collections using:

- Date;
- Milestone;
- Collection Plan;
- Responsible; and
- Details.

#### Collection History

Record actual collections using:

- Date;
- Milestone;
- Collected Amount;
- Collected By; and
- Details.

Every collection-plan and collection-history row must belong to a project.

## 7. Project review sessions

To record a review:

1. Open **Project > Project Master > Review**.
2. Select **New**.
3. Enter the review name and date.
4. In Review History, add one row for each project.
5. Enter the internal review, high-level review, timeline, task-frozen status,
   completion percentage, remarks, and next action as needed.
6. Enter the customer review, customer timeline, customer task-frozen status,
   and customer completion percentage as needed.
7. Save the review session.

Sales Person, Functional Consultant, and Project Coordinators are displayed
from the selected project.

A user can access a review session only when the user can read every project
linked to that session. If even one linked project is inaccessible—including
an archived project in another restricted scope—the entire review session is
hidden and direct access is rejected.

## 8. Project locking

An Odoo user with Administration/Settings access can lock a project:

1. Open the project form.
2. Select **Lock** in the header.
3. Confirm that **Unlock** replaces the Lock button.

While locked, users cannot change:

- the project record and project form tabs;
- credential or financial details;
- collection plans or collection history; or
- linked review information and review sessions.

If a review session contains a locked project, changes to that review session
are blocked. An SBS Project Admin must also unlock a project before deleting
it.

Locking does not replace standard task permissions and does not lock task
records. Use task access roles and normal Odoo task controls for task workflow.

To make an approved correction, an Odoo Administrator must select **Unlock**,
allow the change, and lock the project again when appropriate.

## 9. Task workflows

### 9.1 Standard task user

A standard task user can continue to create and edit tasks allowed by Odoo's
normal project and follower rules. The module only changes deletion: task
deletion requires SBS Project Admin.

### 9.2 Read Task Only user

To create a task:

1. Confirm the user can access the project. For a follower-only project, add
   the user as a follower first.
2. Open **Project > Tasks**.
3. Select **New**.
4. Select the accessible project and enter the task information.
5. Save the task.

After saving, the user can read the task and use its chatter, followers, and
activities, but cannot edit or delete the task. Kanban dragging and task-stage
group maintenance are disabled for this role.

Read Task Only includes Timesheets access, so this role can run the task timer
and log its own time even though it cannot edit the task itself.

### 9.3 Deleting a task

Only an SBS Project Admin can delete a task. This applies even when another
user would normally have delete access through standard Project groups.

### 9.4 The task work timer

The timer records how long a user works on a task and writes that time to the
task timesheet. It requires the Timesheets application. Both SBS Project User
and Read Task Only include the necessary Timesheets access, so no separate
Timesheets role has to be assigned.

Before the timer appears, the task must belong to a project and that project
must have Timesheets enabled. The user must also be linked to an employee
record, otherwise the time cannot be written.

To record time:

1. Open the task. The task header shows **Start**.
2. Select **Start**. The header shows a live counter in HH:MM:SS.
3. Select **End** when the work is finished. The counter stops and the
   **Log Time to Timesheet** window opens.
4. Review **Counted Time**, set the **Date** and a **Description**, and adjust
   **Time to Log** if less time should be recorded.
5. Select **Add to Timesheet**.

The window offers two other choices. **Keep for Later** closes it and leaves the
counted time pending; the task then shows **Log Time** so the window can be
reopened. **Discard Timer** deletes the counted time without recording it.

Rules that apply to the timer:

- One timer runs at a time per user. Start on a second task is refused until the
  running timer is ended.
- Two different users may time the same task at the same time.
- Time to Log may be reduced but never increased. The limit is measured from the
  timer itself, so it holds regardless of how the window is submitted.
- The time is always recorded against the task the timer was started on.
- A pending count must be logged or discarded before the timer can be started
  again on the same task.

### 9.5 Correcting recorded time

Once time reaches the timesheet, only an SBS Project Admin can change or delete
that line. In the task **Timesheets** tab, other users see those lines as
read-only.

The timer does not replace ordinary timesheet entry. Users with Timesheets
access may still record time in the Timesheets application for work that was
never timed, including work on earlier dates. Only the correction of an existing
task timesheet line is restricted.

## 10. Searching and reporting

Project Summary supports searching and grouping by fields including:

- project name and priority;
- Project Director;
- Functional Consultant and Developer;
- Risk Level and Risk Factor; and
- Delivery Type.

Available quick filters include assigned Functional Consultant, risk levels,
AMC, Development, and Payment Pending.

Use the specialized Project Master menus for focused operational lists. The
Credentials and Financials menus appear only when the corresponding role is
assigned.

## 11. Multi-company and record visibility

- Project and task visibility continues to follow Odoo company and project
  privacy rules.
- Credential, financial, collection, review-line, and other project-linked
  records follow access to their related project.
- A user cannot use a specialized menu to bypass project access.
- Archived projects are still considered when the module evaluates whether a
  linked record or review session is safe to show.

## 12. Troubleshooting

| Symptom | Likely reason and action |
|---|---|
| Project Master is not visible | Assign an SBS Project Role to the user. |
| A project is missing | Check company access, project privacy, and follower status. |
| New/Delete is unavailable on projects | Only SBS Project Admin can manually create or delete projects. |
| A task cannot be edited | Check whether Read Task Only is assigned. |
| A task cannot be deleted | Task deletion requires SBS Project Admin. |
| Credentials or Financials is missing | Assign the appropriate SBS Project Role or the combined role. |
| Credential or financial record is missing from its list | Confirm the user can read the related project. |
| A project cannot be changed | Check whether the project is locked. An Odoo Administrator must unlock it. |
| Hybrid cannot be changed to Internal | Remove all manually maintained team entries from every team field. |
| An internal user is missing from team selection | Confirm the Odoo user is internal, active, and not a portal/shared user. |
| A review session is missing | The user cannot read at least one project included in the session. |
| Priority order looks unexpected | Lower positive values come first; zero comes last. |
| A negative priority is rejected | Use zero or a positive whole number. |
| Timesheet creation is unavailable | Confirm the project has Timesheets enabled and that the user is linked to an employee record. Timesheets itself is installed automatically with this module. |
| The Start button is missing on a task | The task has no project, or its project does not have Timesheets enabled. |
| Ending a timer reports that no time was counted | The timer was stopped in the same second it started; nothing is recorded and the timer is removed. |
| A counted time cannot be logged | Time to Log may be reduced but never raised above the counted time. |

## 13. Upgrade note for administrators

When upgrading from the legacy project-field storage to version 19.0.2.0.0:

- existing credential and financial values are migrated to dedicated records;
- existing project field names remain available for compatibility;
- internal-user team entries are synchronized automatically; and
- collection rows without a project stop the upgrade with a corrective error.

If the upgrade reports project-less collection records, assign a project to
each listed record and run the module upgrade again. The migration deliberately
does not guess or discard financial data.


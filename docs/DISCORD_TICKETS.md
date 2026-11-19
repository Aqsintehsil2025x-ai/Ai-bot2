# Discord support tickets

The bot provides a persistent button-based support ticket flow.

## Setup

1. Invite the bot with **Manage Channels**, **View Channels**, **Send Messages**, and **Read Message History** permissions.
2. Create a support role and (optionally) a category and log channel.
3. Run `/ticketpanel` and select the support role, category, and log channel if desired.
4. Members use the panel button to open a private channel.
5. The ticket opener, configured support role, and bot can view the channel. Other members cannot.
6. The opener, support role, or a server manager can close the ticket. The channel is retained as a read-only archive for the opener.

Ticket panel and close buttons are persistent across bot restarts. Open ticket records are stored in `tickets.json` and included in the existing JSON backup process.

## Operational notes

- Each member may have one open ticket per server.
- Closed tickets are retained; they are not automatically deleted.
- Configure a log channel if you want a closure notice.
- The bot must be above the support role in the server role hierarchy and have channel-management permissions.


## Automatic join role

Use `/otorol @role` to assign a role to each new member. Run `/otorol` without a role to disable the per-server setting. The bot must have Manage Roles and its highest role must be above the selected role.

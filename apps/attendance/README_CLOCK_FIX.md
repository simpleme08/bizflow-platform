# Time clock state

The employee clock page enables Clock In only when the authenticated employee has an active shift assignment for the current Philippine date and is active. Clock Out is enabled only when an open attendance record exists.

For the built-in `demo.juan` account, run `python manage.py seed_demo` against the local database before testing. The seed creates Juan Cruz, his Day Shift assignment, and today's demo attendance state.

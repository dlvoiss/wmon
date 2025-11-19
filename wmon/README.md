Raspberry Pi based weather monitoring station using python, SQL
(Maria DB) for server-side functions and php, SQL and a bit of
Javascript for the user interface.  Refer to the DOCUMENTS directory
for project information and hardware components overview.

config.py and HTML/config.php files need to be added in order
to access the mysql database.

config.py contain the two lines shown below. You need to replace
<dbuser> and <dbpass> with your own database user-id and password:

dbuser = '<dbuser>'
dbpwd = '<dbpass>'

HTML/config.php contains the three lines shown below. You need to replace
<dbuser> and <dbpass> with your own database user-id and password:

<?php
$user = '<dbuser>';
$pass = '<dbpass>';

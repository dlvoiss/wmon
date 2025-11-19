<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="style.css">
</head>
<h1>
Thread & Process Aliveness
</h1>

<?php
$host = '127.0.0.1';
$db   = 'weather';
require 'config.php';
$charset = 'utf8mb4';
$tbl = 'monthdata';

$dsn = "mysql:host=$host;dbname=$db;charset=$charset";
$options = [
    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::ATTR_EMULATE_PREPARES   => false,
];
try {
     $pdo = new PDO($dsn, $user, $pass, $options);
} catch (\PDOException $e) {
     throw new \PDOException($e->getMessage(), (int)$e->getCode());
     echo " DB Error" . "<br> <br>";
}

echo
    "<table border='2'>
    <tr>
    <th style=\"text-align:left\">Thread/Process</th>
    <th></th>
    <th style=\"text-align:left\">Last Alive</th>
    </tr>"
    ;

$sql = "SELECT id, id_str, tmstamp FROM keepalive";

$statement = $pdo->query($sql);

while ($row = $statement->fetch()) {

    $thrd_id = $row['id'];
    $thrd = $row['id_str'];
    $alive_ts = $row['tmstamp'];

    echo "<tr>";
    echo "<td style=\"text-align:left\"><b>" . $row['id_str'] . "</b></td>";
    echo "<td style=\"text-align:left\"><b> </b></td>";
    echo "<td style=\"text-align:left\"><b>" . $row['tmstamp'] . "</b></td>";
    echo "</tr>";
}
echo "</table>";
?>

</html>

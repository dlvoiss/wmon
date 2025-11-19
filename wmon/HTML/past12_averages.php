<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="style.css">
</head>
<h1>
Past Year Averages by Month
</h1>

<?php
$host = '127.0.0.1';
$db   = 'weather';
require 'config.php';
$charset = 'utf8mb4';
$tbl = 'monthavg';

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

$null_time = '0000-00-00 00:00:00';

echo
    "<table border='2'>
    <tr>
      <th style=\"text-align:left\">Month</th>
      <th></th>
      <th style=\"text-align:left\">Average</th>
      <th></th>
      <th style=\"text-align:left\"></th>
      <th style=\"text-align:right\">Average</th>
    </tr>"
    ;

#$sql = "SELECT id, month, avgdaytimetempf,avgnighttimetempf, mintempfts, mintempf, maxtempfts, maxtempf, minhumts, minhum, maxhumts, maxhum, lowmBts, lowmB, highmBts, highmB FROM monthdata";

$sql = "SELECT id, month, avgdaytimetempf,avgnighttimetempf,avghightempf,avglowtempf FROM monthavg";

$statement = $pdo->query($sql);

while ($row = $statement->fetch()) {

  $id = $row['id'];

  if ($id != 13) {
    echo "<tr>";
      echo "<td style=\"text-align:left\"><b>" . $row['month'] . "</b></td>";
      echo "<td style=\"text-align:left\">Daytime</td>";
      echo "<td style=\"text-align:right\"><b>" . $row['avgdaytimetempf'] . "</b> F</td>";
      echo "<td style=\"text-align:left\"></td>";
      echo "<td>Average High</td>";
      echo "<td><b>" . $row['avghightempf'] . "</b> F</td>";
    echo "</tr>";

    echo "<tr>";
      echo "<td style=\"text-align:left\"></td>";
      echo "<td style=\"text-align:left\">Nighttime</td>";
      echo "<td style=\"text-align:right\"><b>" . $row['avgnighttimetempf'] . "</b> F</td>";
      echo "<td style=\"text-align:left\"></td>";
      echo "<td>Average Low</td>";
      echo "<td><b>" . $row['avglowtempf'] . "</b> F</td>";
    echo "</tr>";
  }
}
echo "</table>";
?>

<p>
<b>Daytime</b>:
Average of readings at 10 minute intervals between Sunrise and Sunset<br>
<b>Nighttime</b>:
Average of readings at 10 minute intervals between Sunset and Sunrise<br>
<b>Average High</b>:
Average of the highest reading from each day of the month<br>
<b>Average Low</b>:
Average of the low reading from each day of the month<br>
</p>

</html>

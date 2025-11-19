<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="style.css">
</head>
<h1>
Wind Direction Readings
</h1>

<?php
$host = '127.0.0.1';
$db   = 'weather';
require 'config.php';
$charset = 'utf8mb4';
$tbl = 'windrain';

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
    <th style=\"text-align:left\">Resistor value</th>
    <th style=\"text-align:left\">Resistor voltage</th>
    <th style=\"text-align:left\">Resistor Dir</th>
    <th style=\"text-align:left\">Dir</th>
    <th style=\"text-align:left\">Hall Magnetic</th>
    <th style=\"text-align:left\">Hall Sensor Dir</th>
    <th style=\"text-align:left\">Hall Degrees</th>
    <th style=\"text-align:left\">Hall Sensor Value</th>
    <th style=\"text-align:left\">Hall Sensor Voltage</th>
    </tr>"
    ;

$sql = "SELECT id, tmstamp, wind_r_volts, wind_r_val, dir, winddir, wind_h_volts, wind_h_val, wind_degree, wind_dir_str, wind_mag_dir_str FROM windrain where recordType='AVG' order by tmstamp desc limit 50";

$statement = $pdo->query($sql);

while ($row = $statement->fetch()) {

    $r_volts = $row['wind_r_volts'];
    $r_val = $row['wind_r_val'];
    $h_volts = $row['wind_h_volts'];
    $h_val = $row['wind_h_val'];

    echo "<tr>";
    echo "<td style=\"text-align:left\"><b>" . $row['wind_r_val'] . "</b></td>";
    echo "<td style=\"text-align:left\"><b>" . $row['wind_r_volts'] . "</b></td>";
    echo "<td style=\"text-align:left\"><b>" . $row['winddir'] . "</b></td>";
    echo "<td style=\"text-align:left\"><b>" . $row['dir'] . "</b></td>";
    echo "<td style=\"text-align:left\"><b>" . $row['wind_mag_dir_str'] . "</b></td>";
    echo "<td style=\"text-align:left\"><b>" . $row['wind_dir_str'] . "</b></td>";
    echo "<td style=\"text-align:left\"><b>" . $row['wind_degree'] . "</b></td>";
    echo "<td style=\"text-align:left\"><b>" . $row['wind_h_val']. "</b></td>";
    echo "<td style=\"text-align:left\"><b>" . $row['wind_h_volts'] . "</b></td>";
    echo "</tr>";
}
echo "</table>";
?>

</html>

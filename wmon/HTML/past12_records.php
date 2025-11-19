<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="style.css">
</head>
<h1>
Past 12 Months Records by Month
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

$null_time = '0000-00-00 00:00:00';

echo
    "<table border='2'>
    <tr>
    <th style=\"text-align:left\">Month</th>
    <th></th>
    <th style=\"text-align:left\">Date</th>
    <th style=\"text-align:right\">Temp.</th>
    <th style=\"text-align:left\">Date</th>
    <th style=\"text-align:right\">Humidity</th>
    <th style=\"text-align:left\">Date</th>
    <th style=\"text-align:right\">Barometer</th>
    </tr>"
    ;

$sql = "SELECT id, month, mintempfts, mintempf, maxtempfts, maxtempf, minhumts, minhum, maxhumts, maxhum, lowmBts, lowmB, highmBts, highmB FROM monthdata";

$statement = $pdo->query($sql);

while ($row = $statement->fetch()) {

    $max_temp_ts = $row['maxtempfts'];
    $max_hum_ts = $row['maxhumts'];
    $max_mb_ts = $row['highmBts'];
    $min_temp_ts = $row['mintempfts'];
    $min_hum_ts = $row['minhumts'];
    $min_mb_ts = $row['lowmBts'];

    echo "<tr>";
    echo "<td style=\"text-align:left\"><b>" . $row['month'] . "</b></td>";
    echo "<td style=\"text-align:left\"><b>Highs</b></td>";
    if ($max_temp_ts == $null_time) { 
        echo "<td></td>";
        echo "<td></td>";
    } else {
        echo "<td style=\"text-align:left\">" . $max_temp_ts . "</td>";
        echo "<td style=\"text-align:right\"><b>" . $row['maxtempf'] . "</b> F</td>";
    }
    if ($max_hum_ts == $null_time) { 
        echo "<td></td>";
        echo "<td></td>";
    } else {
        echo "<td style=\"text-align:left\">" . $row['maxhumts'] . "</td>";
        echo "<td style=\"text-align:right\"><b>" . $row['maxhum'] . "</b>%</td>";
    }
    if ($max_mb_ts == $null_time) { 
        echo "<td></td>";
        echo "<td></td>";
    } else {
        echo "<td style=\"text-align:left\">" . $row['highmBts'] . "</td>";
        echo "<td style=\"text-align:right\"><b>" . $row['highmB'] . "</b> mB</td>";
    }
    echo "</tr>";
    echo "<tr>";
    echo "<td style=\"text-align:left\"></td>";
    echo "<td style=\"text-align:left\"><b>Lows</b></td>";
    if ($min_temp_ts == $null_time) { 
        echo "<td></td>";
        echo "<td></td>";
    } else {
        echo "<td style=\"text-align:left\">" . $min_temp_ts . "</td>";
        echo "<td style=\"text-align:right\"><b>" . $row['mintempf'] . "</b> F</td>";
    }
    if ($min_hum_ts == $null_time) { 
        echo "<td></td>";
        echo "<td></td>";
    } else {
        echo "<td style=\"text-align:left\">" . $min_hum_ts . "</td>";
        echo "<td style=\"text-align:right\"><b>" . $row['minhum'] . "</b>%</td>";
    }
    if ($min_mb_ts == $null_time) { 
        echo "<td></td>";
        echo "<td></td>";
    } else {
        echo "<td style=\"text-align:left\">" . $min_mb_ts . "</td>";
        echo "<td style=\"text-align:right\"><b>" . $row['lowmB'] . "</b> mB</td>";
    }
    echo "</tr>";
}
echo "</tr></table>";
?>

<h1>
Past 12 Months Records
</h1>

<?php
# Find maximum temperature from monthdata across all 12 months
$sql = "SELECT max(maxtempf) FROM monthdata";
$statement = $pdo->query($sql);
$row = $statement->fetch();
$maxtemp = $row['max(maxtempf)'];
#echo "<p>Maximum Temperature: " . $maxtemp . "</p>";

$sql = "SELECT month,maxtempfts,maxtempf FROM monthdata where maxtempf=" . $maxtemp;
#echo $sql;
$statement = $pdo->query($sql);
$row = $statement->fetch();

$monTempMax = $row['month'];
$TempMax = $row['maxtempf'];

# Find minimum temperature from monthdata across all 12 months
$sql = "SELECT min(mintempf) FROM monthdata";
$statement = $pdo->query($sql);
$row = $statement->fetch();
$mintemp = $row['min(mintempf)'];
#echo "<p>Minimum Temperature: " . $mintemp . "</p>";

$sql = "SELECT month,mintempfts,mintempf FROM monthdata where mintempf=" . $mintemp;
$statement = $pdo->query($sql);
$row = $statement->fetch();
$monTempMin = $row['month'];
$TempMin = $row['mintempf'];

#echo "<p>Temperature: MAX: " . $monTempMax . ": <b>" . $TempMax . "</b> F";
#echo "; MIN: " . $monTempMin . ": <b>" . $TempMin . "</b> F</p>";

# Find maximum humidity from monthdata across all 12 months
$sql = "SELECT max(maxhum) FROM monthdata";
$statement = $pdo->query($sql);
$row = $statement->fetch();
$maxhum = $row['max(maxhum)'];
#echo "<p>Maximum Temperature: " . $maxhum . "</p>";

$sql = "SELECT month,maxhumts,maxhum FROM monthdata where maxhum=" . $maxhum;
#echo $sql;
$statement = $pdo->query($sql);
$row = $statement->fetch();

$monHumMax = $row['month'];
$HumMax = $row['maxhum'];

# Find minimum humidity from monthdata across all 12 months
$sql = "SELECT min(minhum) FROM monthdata";
$statement = $pdo->query($sql);
$row = $statement->fetch();
$minhum = $row['min(minhum)'];
#echo "<p>Minimum Temperature: " . $minhum . "</p>";

$sql = "SELECT month,minhumts,minhum FROM monthdata where minhum=" . $minhum;
$statement = $pdo->query($sql);
$row = $statement->fetch();
$monHumMin = $row['month'];
$HumMin = $row['minhum'];

#echo "<p>Humidity: MAX: " . $monHumMax . ": <b>" . $HumMax . "</b>%";
#echo "; MIN: " . $monHumMin . ": <b>" . $HumMin . "</b>%</p>";

# Find maximum pressure from monthdata across all 12 months
$sql = "SELECT max(highmB) FROM monthdata";
$statement = $pdo->query($sql);
$row = $statement->fetch();
$maxmB = $row['max(highmB)'];
#echo "<p>Maximum Temperature: " . $maxmB . "</p>";

$sql = "SELECT month,highmBts,highmB FROM monthdata where highmB=" . $maxmB;
#echo $sql;
$statement = $pdo->query($sql);
$row = $statement->fetch();

$monMbMax = $row['month'];
$MbMax = $row['highmB'];

# Find minimum pressure from monthdata across all 12 months
$sql = "SELECT min(lowmB) FROM monthdata";
$statement = $pdo->query($sql);
$row = $statement->fetch();
$minmB = $row['min(lowmB)'];
#echo "<p>Minimum Temperature: " . $minmB . "</p>";

$sql = "SELECT month,lowmBts,lowmB FROM monthdata where lowmB=" . $minmB;
$statement = $pdo->query($sql);
$row = $statement->fetch();
$monMbMin = $row['month'];
$MbMin = $row['lowmB'];

#echo "<p>Pressure: MAX: " . $monMbMax . ": <b>" . $MbMax . "</b> mB";
#echo "; MIN: " . $monMbMin . ": <b>" . $MbMin . "</b> mB</p>";

echo
    "<table border='2'>
    <tr>
      <th></th>
      <th style=\"text-align:left\">Maximum</th>
      <th></th>
      <th style=\"text-align:left\">Minimum</th>
      <th></th>
    </tr>"
    ;
echo
    "<tr>
      <td style=\"text-align:left\"><b>Temperature&nbsp</b></td>
      <td style=\"text-align:left\">" . $monTempMax . "</td>
      <td style=\"text-align:right\"><b>" . $TempMax . "</b> F</td>
      <td style=\"text-align:left\">" . $monTempMin . "</td>
      <td style=\"text-align:right\"><b>" . $TempMin . "</b> F</td>
    </tr>
    <tr>
      <td style=\"text-align:left\"><b>Humidity</b></td>
      <td style=\"text-align:left\">" . $monHumMax . "</td>
      <td style=\"text-align:right\"><b>" . $HumMax . "</b>%</td>
      <td style=\"text-align:left\">" . $monHumMin . "</td>
      <td style=\"text-align:right\"><b>" . $HumMin . "</b>%</td>
    </tr>
    <tr>
      <td style=\"text-align:left\"><b>Pressure</b></td>
      <td style=\"text-align:left\">" . $monMbMax . "</td>
      <td style=\"text-align:right\"><b>" . $MbMax . "</b> mB&nbsp</td>
      <td style=\"text-align:left\">" . $monMbMin . "</td>
      <td style=\"text-align:right\"><b>" . $MbMin . "</b> mB</td>
    </tr>
  <table>"
  ;
?>

</html>

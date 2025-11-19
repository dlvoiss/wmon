<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="style.css">
<h1>
Weather Conditions at 1622 Columbia Dr.
</h1>
<p>
<?php
#echo "<br>Refresh at: " . date('Y-m-d H:i:s') . "<br>";
?>

<?php
$host = '127.0.0.1';
$db   = 'weather';
require 'config.php';
$charset = 'utf8mb4';
$tbl = 'readings';

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
?>

<?php
# Confirm readings are up to date
$rmt =  $pdo->query('select tmstamp from readings where recordType="LOCAL" order by tmstamp desc limit 1');
$row = $rmt->fetch();
$tmstamp = $row['tmstamp'];
#echo "<br>Last LOCAL reading: " . $tmstamp . "<br>";
#$rmt =  $pdo->query('select tmstamp from readings where recordType="REMOTE" order by tmstamp desc limit 1');
#$row = $rmt->fetch();
#$rmt_tmstamp = $row['tmstamp'];
#echo "<br>Last REMOTE reading: " . $rmt_tmstamp . "<br>";
?>

<table border='2'>
  <tr>
    <th style="text-align:left">UI Refresh At</th>
    <th style="text-align:left">&nbsp</th>
    <th style="text-align:left">Server Refresh</th>
  </tr>
  <tr>
<?php
    echo "<td><b>" . date('Y-m-d H:i:s') . "</b></td>";
    echo "<td></td>";
    echo "<td>" . $tmstamp . "</td>";
?>
  </tr>
</table>
<br>
<form action="thread_status.php" method="post" target="_blank">
  <p>
  <input type="submit" value="Thread Status">
  </p>
</form>


<?php
# Get other current stats from current_stats table
$rmt =  $pdo->query('select * from current_stats limit 1');
$row = $rmt->fetch();
$windtmstamp = $row['tmstamp'];
$windspeed = $row['windspeed'];
$winddegree = $row['wind_degree'];
$winddir = $row['wind_dir_str'];
$windgust = $row['gust'];
$avg1min = $row['windavg1'];
$avg5min = $row['windavg5'];
$max1hr = $row['windmax1hour'];
$maxtoday = $row['windmaxtoday'];
$raintoday = $row['rainfall_today'];
$sunrise = $row['sunrise'];
$sunset = $row['sunset'];

#echo "<p>Sunrise: " . $sunrise . " Sunset: " . $sunset . "</p>";
#echo "<p>Wind: " . $windspeed . " mph, Dir: " . $winddir . ", Gusts: " . $windgust . " mph</p>";
#echo "<p>Wind degree: " . $winddegree . " degrees</p>";
#echo "<p>Wind 1 Minute Avg: " . $avg1min . " mph, Wind 5 minute Avg: " . $avg5min . " mph</p>";
#echo "<p>Rain Today: " . $raintoday . " inches</p>";

# Get rain fall amount from one hour ago
$rnhour = $pdo->query('SELECT tmstamp, rainfall, rainfall_counter FROM windrain WHERE recordType="AVG" and tmstamp >= NOW() - INTERVAL 1 HOUR ORDER by tmstamp ASC limit 1');
$row = $rnhour->fetch();
$rain1hour = $row['rainfall'];
$tm = $row['tmstamp'];
$ctr = $row['rainfall_counter'];

# Calculate rainfall over last hour
$rainlasthour = $raintoday - $rain1hour;

#echo "<p>Current rain: " . $raintoday . " rain 1 hour ago: " . $rain1hour . "</p>";
#echo "<p>Rain fall over past hour: " . $rainlasthour . " inches</p>";

?>

<table border='2'>
  <tr>
    <th style="text-align:left">Sunrise</th>
    <th style="text-align:left">&nbsp</th>
    <th style="text-align:left">Sunset</th>
  </tr>
  <tr>
<?php
    echo "<td><b>" . $sunrise . "</b></td>";
    echo "<td></td>";
    echo "<td><b>" . $sunset . "</b></td>";
?>
  </tr>
</table>

<h2>Current Weather</h2>

<script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
<script type="text/javascript">

      google.charts.load('current', {'packages':['gauge']});
      google.charts.setOnLoadCallback(drawChartF);

      function drawChartF() {

        var data = google.visualization.arrayToDataTable([
          ['Label', 'Value'],
<?php
      $sql = "SELECT tempdhtf FROM currentreadings WHERE id = 1";
      $weather = $pdo->query($sql);
      $row = $weather->fetch();
      echo "['Temp F',".$row['tempdhtf']."],";
?>
        ]);

        var options = {
          width: 600, height: 250,
          min: 20, max: 130,
          redFrom:100, redTo: 130,
          yellowFrom:20, yellowTo: 32,
          minorTicks: 5
        };

        var chart = new google.visualization.Gauge(document.getElementById('chart_temp'));

        chart.draw(data, options);
      }
</script>

<script type="text/javascript">

      google.charts.load('current', {'packages':['gauge']});
      google.charts.setOnLoadCallback(drawChartF);

      function drawChartF() {

        var data = google.visualization.arrayToDataTable([
          ['Label', 'Value'],
<?php
      $sql = "SELECT baromB FROM currentreadings WHERE id = 1";
      $weather = $pdo->query($sql);
      $row = $weather->fetch();
      echo "['milliBar',".$row['baromB']."],";
?>
        ]);

        var options = {
          width: 600, height: 250,
          min: 970, max: 1035,
          yellowFrom:970, yellowTo: 995,
          minorTicks: 5
        };

        var chart = new google.visualization.Gauge(document.getElementById('chart_baro'));

        chart.draw(data, options);
      }
</script>

<script type="text/javascript">

      google.charts.load('current', {'packages':['gauge']});
      google.charts.setOnLoadCallback(drawChartF);
  
      function drawChartF() {

        var data = google.visualization.arrayToDataTable([
          ['Label', 'Value'],
<?php
      $sql = "SELECT humidity FROM currentreadings WHERE id = 1";
      $weather = $pdo->query($sql);
      $row = $weather->fetch();
      echo "['Humidity (%)',".$row['humidity']."],";
?>
        ]);

        var options = {
          width: 600, height: 250,
          min: 0, max: 100,
          minorTicks: 5
        };

        var chart = new google.visualization.Gauge(document.getElementById('chart_humidity'));

        chart.draw(data, options);
      }
</script>

</head>
  <body>
    <table>
      <tr>
      <td>
      <div id="chart_temp" style="border: medium solid transparent; width: 250px; height: 250px;"></div>
      </td>
      <td>
      <div id="chart_baro" style="border: medium solid transparent; width: 250px; height: 250px;"></div>
      </td>
      <td>
      <div id="chart_humidity" style="border: medium solid transparent; width: 250px; height: 250px;"></div>
      </td>
      </tr>
    </table>

<br>
<br>
<table border='2'>
  <tr>
    <th style="text-align:left">Wind</th>
    <th style="text-align:left">&nbsp</th>
    <th style="text-align:left">Dir</th>
    <th style="text-align:left">&nbsp</th>
    <th style="text-align:left">Dir</th>
    <th style="text-align:left">&nbsp</th>
    <th style="text-align:left">Gusts</th>
    <th style="text-align:left">&nbsp</th>
    <th style="text-align:left">Date</th>
  </tr>
  <tr>
<?php
    echo "<td><b>" . $windspeed . "</b> mph</td>";
    echo "<td></td>";
    echo "<td><b>" . $winddegree . "</b></td>";
    echo "<td></td>";
    echo "<td><b>" . $winddir . "</b></td>";
    echo "<td></td>";
    echo "<td><b>" . $windgust . "</b> mph</td>";
    echo "<td></td>";
    echo "<td>" . $windtmstamp . "</td>";
?>
  </tr>
  <tr>
    <th style="text-align:left">1-Min Avg</th>
    <th style="text-align:left">&nbsp</th>
    <th style="text-align:left">5-Min Avg</th>
    <th style="text-align:left">&nbsp</th>
    <th style="text-align:left">Max Past Hour</th>
    <th style="text-align:left">&nbsp</th>
    <th style="text-align:left">Max Today</th>
    <th style="text-align:left"></th>
    <th style="text-align:left"> </th>
    <th style="text-align:left"></th>
  </tr>
  <tr>
<?php
    echo "<td><b>" . $avg1min . "</b> mph</td>";
    echo "<td></td>";
    echo "<td><b>" . $avg5min . "</b> mph</td>";
    echo "<td></td>";
    echo "<td><b>" . $max1hr . "</b> mph</td>";
    echo "<td></td>";
    echo "<td><b>" . $maxtoday . "</b> mph</td>";
    echo "<td> </td>";
    echo "<td> </td>";
    echo "<td> </td>";
?>
  </tr>
  <tr>
    <th style="text-align:left">Rain Today</th>
    <th style="text-align:left">&nbsp</th>
    <th style="text-align:left"> </th>
    <th style="text-align:left">&nbsp</th>
    <th style="text-align:left">Rain Past Hour </th>
    <th style="text-align:left">&nbsp</th>
    <th style="text-align:left"> </th>
    <th style="text-align:left"></th>
    <th style="text-align:left"> </th>
    <th style="text-align:left"></th>
  </tr>
  <tr>
<?php
    echo "<td><b>" . $raintoday . "</b> inches</td>";
    echo "<td></td>";
    echo "<td><b> </td>";
    echo "<td></td>";
    echo "<td><b>" . $rainlasthour . "</b> inches</td>";
    echo "<td></td>";
    echo "<td><b> </td>";
    echo "<td> </td>";
    echo "<td> </td>";
    echo "<td> </td>";
?>
  </tr>
</table>
<br>
<?php
  $sql = "SELECT baromB FROM readings WHERE recordType='LOCAL' order by tmstamp desc limit 1";
  $weather = $pdo->query($sql);
  $row = $weather->fetch();
  $baroMB_now = $row['baromB'];

  $sql = "SELECT baromB FROM readings where recordType='LOCAL' and tmstamp >= NOW()- INTERVAL 1 HOUR limit 1";
  $weather = $pdo->query($sql);
  $row = $weather->fetch();
  $baroMB_1hour_ago = $row['baromB'];

  $sql = "SELECT baromB FROM readings where recordType='LOCAL' and tmstamp >= NOW()- INTERVAL 2 HOUR limit 1";
  $weather = $pdo->query($sql);
  $row = $weather->fetch();
  $baroMB_2hour_ago = $row['baromB'];

  $sql = "SELECT baromB FROM readings where recordType='LOCAL' and tmstamp >= NOW()- INTERVAL 4 HOUR limit 1";
  $weather = $pdo->query($sql);
  $row = $weather->fetch();
  $baroMB_4hour_ago = $row['baromB'];

  $sql = "SELECT baromB FROM readings where recordType='LOCAL' and tmstamp >= NOW()- INTERVAL 6 HOUR limit 1";
  $weather = $pdo->query($sql);
  $row = $weather->fetch();
  $baroMB_6hour_ago = $row['baromB'];

  $sql = "SELECT baromB FROM readings where recordType='LOCAL' and tmstamp >= NOW()- INTERVAL 12 HOUR limit 1";
  $weather = $pdo->query($sql);
  $row = $weather->fetch();
  $baroMB_12hour_ago = $row['baromB'];

  $sql = "SELECT baromB FROM readings where recordType='LOCAL' and tmstamp >= NOW()- INTERVAL 1 DAY limit 1";
  $weather = $pdo->query($sql);
  $row = $weather->fetch();
  $baroMB_24hour_ago = $row['baromB'];

  $lastOneHour = $baroMB_now - $baroMB_1hour_ago;
  $lastTwoHour = $baroMB_now - $baroMB_2hour_ago;
  $lastFourHour = $baroMB_now - $baroMB_4hour_ago;
  $lastSixHour = $baroMB_now - $baroMB_6hour_ago;
  $last12Hour = $baroMB_now - $baroMB_12hour_ago;
  $last24Hour = $baroMB_now - $baroMB_24hour_ago;

  #echo "<p>BAROMETER:       " . $baroMB_now . "</p>";
  #echo "<p>BAROMETER - 1HR: " . $baroMB_1hour_ago . "</p>";
  #echo "<p>BAROMETER - 2HR: " . $baroMB_2hour_ago . "</p>";
  #echo "<p>BAROMETER - 4HR: " . $baroMB_4hour_ago . "</p>";
  #echo "<p>BAROMETER - 6HR: " . $baroMB_6hour_ago . "</p>";
  #echo "<p>BAROMETER - 12HR: " . $baroMB_12hour_ago . "</p>";
  #echo "<p>BAROMETER - 24HR: " . $baroMB_24hour_ago . "</p>";

  #echo "<p>BAROMETER CHANGE (1HR): " . $lastOneHour . "</p>";
  #echo "<p>BAROMETER CHANGE (2HR): " . $lastTwoHour . "</p>";
  #echo "<p>BAROMETER CHANGE (4HR): " . $lastFourHour . "</p>";
  #echo "<p>BAROMETER CHANGE (6HR): " . $lastSixHour . "</p>";
  #echo "<p>BAROMETER CHANGE (12HR): " . $last12Hour . "</p>";
  #echo "<p>BAROMETER CHANGE (24HR): " . $last24Hour . "</p>";

  if ($lastOneHour >= "0.2") {
    $lastHour = "RISING";
  } elseif ($lastOneHour <= "-0.2") {
    $lastHour = "FALLING";
  } else {
    $lastHour = "STEADY";
  }

  if ($lastTwoHour >= "0.5") {
    $lastTwo = "RISING";
  } elseif ($lastTwoHour <= "-0.5") {
    $lastTwo = "FALLING";
  } else {
    $lastTwo = "STEADY";
  }

  if ($lastFourHour >= "0.5") {
    $lastFour = "RISING";
  } elseif ($lastFourHour <= "-0.5") {
    $lastFour = "FALLING";
  } else {
    $lastFour = "STEADY";
  }

  if ($lastSixHour >= "0.5") {
    $lastSix = "RISING";
  } elseif ($lastSixHour <= "-0.5") {
    $lastSix = "FALLING";
  } else {
    $lastSix = "STEADY";
  }

  if ($last12Hour >= "0.5") {
    $last12 = "RISING";
  } elseif ($last12Hour <= "-0.5") {
    $last12 = "FALLING";
  } else {
    $last12 = "STEADY";
  }

  if ($last24Hour >= "0.5") {
    $last24 = "RISING";
  } elseif ($last24Hour <= "-0.5") {
    $last24 = "FALLING";
  } else {
    $last24 = "STEADY";
  }
?>

<table border='2'>
  <tr>
    <th style="text-align:left">Barometer</th>
    <th style="text-align:left">One<br>Hour Ago</th>
    <th style="text-align:left">Six<br>Hours Ago</th>
    <th style="text-align:left">12<br>Hours Ago</th>
    <th style="text-align:left">24<br>Hours Ago</th>
  </tr>
  <tr>
<?php
    echo "<td style=\"text-align:left; font-size: 100%;\">" . number_format($baroMB_now, 1, '.', '')  . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . number_format($baroMB_1hour_ago, 1, '.', '')  . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . number_format($baroMB_6hour_ago, 1, '.', '')  . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . number_format($baroMB_12hour_ago, 1, '.', '')  . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . number_format($baroMB_24hour_ago, 1, '.', '')  . "<br></td>";
?>
  </tr>
  <tr>
    <td></td>
<?php
    echo "<td style=\"text-align:left; font-size: 100%;\">" . number_format($lastOneHour, 1, '.', '')  . "<br></td>";
    #echo "<td style=\"text-align:left; font-size: 100%;\">" . number_format($lastTwoHour, 1, '.', '')  . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . number_format($lastSixHour, 1, '.', '')  . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . number_format($last12Hour, 1, '.', '')  . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . number_format($last24Hour, 1, '.', '')  . "<br></td>";
?>
  </tr>
  <tr>
    <td></td>
<?php
  if ($lastHour == 'RISING') {
    echo "<td bgcolor=#90EE90>" . $lastHour . "<br></td>";
  } elseif ($lastHour == 'FALLING') {
    echo "<td bgcolor='yellow'>" . $lastHour . "<br></td>";
  } else {
    echo "<td>" . $lastHour . "<br></td>";
  }
  #if ($lastTwo == 'RISING') {
  #  echo "<td bgcolor=#90EE90>" . $lastTwo . "<br></td>";
  #} elseif ($lastTwo == 'FALLING') {
  #  echo "<td bgcolor='yellow'>" . $lastTwo . "<br></td>";
  #} else {
  #  echo "<td>" . $lastTwo . "<br></td>";
  #}
  #if ($lastFour == 'RISING') {
  #  echo "<td bgcolor=#90EE90>" . $lastFour . "<br></td>";
  #} elseif ($lastFour == 'FALLING') {
  #  echo "<td bgcolor='yellow'>" . $lastFour . "<br></td>";
  #} else {
  #  echo "<td>" . $lastFour . "<br></td>";
  #}
  if ($lastSix == 'RISING') {
    echo "<td bgcolor=#90EE90>" . $lastSix . "<br></td>";
  } elseif ($lastSix == 'FALLING') {
    echo "<td bgcolor='yellow'>" . $lastSix . "<br></td>";
  } else {
    echo "<td>" . $lastSix . "<br></td>";
  }
  if ($last12 == 'RISING') {
    echo "<td bgcolor=#90EE90>" . $last12 . "<br></td>";
  } elseif ($last12 == 'FALLING') {
    echo "<td bgcolor='yellow'>" . $last12 . "<br></td>";
  } else {
    echo "<td>" . $last12 . "<br></td>";
  }
  if ($last24 == 'RISING') {
    echo "<td bgcolor=#90EE90>" . $last24 . "<br></td>";
  } elseif ($last24 == 'FALLING') {
    echo "<td bgcolor='yellow'>" . $last24 . "<br></td>";
  } else {
    echo "<td>" . $last24 . "<br></td>";
  }
?>
  </tr>
</table>
<br>
<form action="wind_status.php" method="post" target="_blank">
  <p>
  <input type="submit" value="Wind Status">
  </p>
</form>

<h2>Today: Highs & Lows</h2>

<?php
# Get/update mininum/maximum readings today
$tempToday =  $pdo->query('select * from readingsToday');
$row = $tempToday->fetch();
$tempTodaymin = $row['minTodaydhtf'];
$tempTodaymax = $row['maxTodaydhtf'];
$tempTodaymints = $row['minTodaydhtts'];
$tempTodaymaxts = $row['maxTodaydhtts'];

$humTodaymin = $row['minTodayhumidity'];
$humTodaymax = $row['maxTodayhumidity'];
$humTodaymints = $row['minTodayhumts'];
$humTodaymaxts = $row['maxTodayhumts'];

$baroTodaymin = $row['lowTodaymB'];
$baroTodaymax = $row['highTodaymB'];
$baroTodaymints = $row['lowTodaymbts'];
$baroTodaymaxts = $row['highTodaymbts'];

#echo "<p>TEMP: " . $tempTodaymin . ", " . $tempTodaymax . "</p>";
#echo "<p>HUMIDITY: " . $humTodaymin . ", " . $humTodaymax . "</p>";
#echo "<p>BAROMETER: " . $baroTodaymin . ", " . $baroTodaymax . "</p>";
?>

<table border='2'>
  <tr>
    <th style="text-align:left"> </th>
    <th style="text-align:left">Date</th>
    <th style="text-align:left">Temperature</th>
    <th style="text-align:left">Date</th>
    <th style="text-align:left">Humidity</th>
    <th style="text-align:left">Date</th>
    <th style="text-align:left">Barometer</th>
  </tr>
  <tr>
    <td style="text-align:left; font-weight: bold; font-size: 120%;">Highs<br></td>
<?php
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $tempTodaymaxts . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $tempTodaymax . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $humTodaymaxts . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $humTodaymax . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $baroTodaymaxts . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $baroTodaymax . "<br></td>";
?>
  </tr>
  <tr>
    <td style="text-align:left; font-weight: bold; font-size: 120%;">Lows<br></td>
<?php
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $tempTodaymints . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $tempTodaymin . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $humTodaymints . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $humTodaymin . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $baroTodaymints . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $baroTodaymin . "<br></td>";
?>
  </tr>
</table>

<h2>Past 24 Hours: Highs & Lows</h2>

<?php
# Get/update mininum temperature in last 24 hours

$temp1day =  $pdo->query('select min(tempdhtf), max(tempdhtf), min(humidity), max(humidity), min(baromB), max(baromB) from readings where recordType="LOCAL" and tmstamp >= NOW() - INTERVAL 1 DAY');
$row = $temp1day->fetch();
$temp1min = $row['min(tempdhtf)'];
$temp1max = $row['max(tempdhtf)'];
$hum1min = $row['min(humidity)'];
$hum1max = $row['max(humidity)'];
$baro1min = $row['min(baromB)'];
$baro1max = $row['max(baromB)'];

#echo "<p>TEMP: " . $temp1min . ", " . $temp1max . "</p>";
#echo "<p>HUMIDITY: " . $hum1min . ", " . $hum1max . "</p>";
#echo "<p>BAROMETER: " . $baro1min . ", " . $baro1max . "</p>";


$temp_data = $pdo->query('SELECT * FROM currentreadings where id = 1');
$row = $temp_data->fetch();

$tmstamp = $row['tmstamp'];

$tempf = $row['tempdhtf'];
$minf = $row['mindhtf'];
$mints = $row['mindhtts'];
$maxf = $row['maxdhtf'];
$maxts = $row['maxdhtts'];

$humidity = $row['humidity'];
$minh = $row['minhumidity'];
$minhts = $row['minhumts'];
$maxh = $row['maxhumidity'];
$maxhts = $row['maxhumts'];

$mB = $row['baromB'];
$min_mB = $row['lowmB'];
$min_mBts = $row['lowmbts'];
$max_mB = $row['highmB'];
$max_mBts = $row['highmbts'];

?>

<table border='2'>
  <tr>
    <th style="text-align:left"> </th>
    <th style="text-align:left">Date</th>
    <th style="text-align:left">Temperature</th>
    <th style="text-align:left">Date</th>
    <th style="text-align:left">Humidity</th>
    <th style="text-align:left">Date</th>
    <th style="text-align:left">Barometer</th>
  </tr>
  <tr>
    <td style="text-align:left; font-weight: bold; font-size: 120%;">Highs<br></td>
<?php
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $maxts . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $maxf . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $maxhts . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $maxh . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $max_mBts . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $max_mB . "<br></td>";
?>
  </tr>
  <tr>
    <td style="text-align:left; font-weight: bold; font-size: 120%;">Lows<br></td>
<?php
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $mints . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $minf . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $minhts . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $minh . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $min_mBts . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $min_mB . "<br></td>";
?>
  </tr>
</table>

<form action="action_charts.php" method="post" target="_blank">
  <p>
  <input type="submit" value="24-Hour Charts">
  </p>
</form>

<table border="0">
  <tr>
    <td>
      <form action="action_ndays_chart.php" method="post" target="_blank">
        <p>
        <select name="ndays">
          <option value ="2" selected>2</option>
          <option value ="7">7</option>
          <option value ="30">30</option>
          <option value ="180">180</option>
        </select>
        </p>
    </td>
    <td>
      <p>
      <input type="submit" value="N-days Charts">
      </p>
      </form>
    </td>
  </tr>
</table>

<form action="action_list_history.php" method="post" target="_blank">
  <p>
  <input type="submit" value="24-Hour Data Listing">
  </p>
</form>

<h2>Past 30 Days: Highs & Lows</h2>

<?php
$temp30day =  $pdo->query('select min(tempdhtf), max(tempdhtf), min(humidity), max(humidity), min(baromB), max(baromB) from readings where recordType="LOCAL" and tmstamp >= NOW() - INTERVAL 30 DAY');
$row = $temp30day->fetch();
$temp30min = $row['min(tempdhtf)'];
$temp30max = $row['max(tempdhtf)'];
$hum30min = $row['min(humidity)'];
$hum30max = $row['max(humidity)'];
$baro30min = $row['min(baromB)'];
$baro30max = $row['max(baromB)'];

#echo "<p>TEMP: " . $temp30min . ", " . $temp30max . "</p>";
#echo "<p>HUMIDITY: " . $hum30min . ", " . $hum30max . "</p>";
#echo "<p>BAROMETER: " . $baro30min . ", " . $baro30max . "</p>";

$temp_data = $pdo->query('SELECT * FROM readings30 where id = 1');
$row = $temp_data->fetch();

$tmstamp = $row['tmstamp'];

$min30f = $row['min30dhtf'];
$min30ts = $row['min30dhtts'];
$max30f = $row['max30dhtf'];
$max30ts = $row['max30dhtts'];

$min30humidity = $row['min30humidity'];
$min30humts = $row['min30humts'];
$max30humidity = $row['max30humidity'];
$max30humts = $row['max30humts'];

$min30mb = $row['low30mB'];
$min30mbts = $row['low30mbts'];
$max30mb = $row['high30mB'];
$max30mbts = $row['high30mbts'];
?>

<table border='2'>
  <tr>
    <th style="text-align:left"\> </th>
    <th style="text-align:left"\>Date</th>
    <th style="text-align:left"\>Temperature</th>
    <th style="text-align:left"\>Date</th>
    <th style="text-align:left"\>Humidity</th>
    <th style="text-align:left"\>Date</th>
    <th style="text-align:left"\>Barometer</th>
  </tr>
  <tr>
    <td style="text-align:left; font-weight: bold; font-size: 120%;">Highs<br></td>
<?php
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $max30ts . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $max30f . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $max30humts . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $max30humidity . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $max30mbts . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $max30mb . "<br></td>";
?>
  </tr>
  <tr>
    <td style="text-align:left; font-weight: bold; font-size: 120%;">Lows<br></td>
<?php
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $min30ts . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $min30f . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $min30humts . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $min30humidity . "<br></td>";
    echo "<td style=\"text-align:left; font-size: 100%;\">" . $min30mbts . "<br></td>";
    echo "<td style=\"text-align:left; font-weight: bold; font-size: 120%;\">" . $min30mb . "<br></td>";
?>
  </tr>
</table>

<h2>Records and Averages</h2>
<form action="past12_averages.php" method="post" target="_blank">
  <p>
  <input type="submit" value="Past Year Averages by Month">
  </p>
</form>
<form action="past12_records.php" method="post" target="_blank">
  <p>
  <input type="submit" value="Past Year Records by Month">
  </p>
</form>
<form action="all_time_records.php" method="post" target="_blank">
  <p>
  <input type="submit" value="All-Time Records by Month">
  </p>
</form>

<!-- ####################################################### -->
<!-- -->
<!-- Display CPU Fan and Temperature History -->
<!-- -->
<!-- ####################################################### -->

<h2>CPU History</h2>
<form action="action_cpu.php" method="post" target="_blank">
  <p>
  <input type="submit" value="CPU Fan & Temperature History">
  </p>
</form>

<script src="main.js"></script>


  </body>
</html>

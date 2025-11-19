<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="style.css">
</head>
<h1>
Last 24-Hour Temperatures (10 minute interval)
</h1>

<?php
$ndays = htmlspecialchars($_POST['ndays']);

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

<script type="text/javascript" src="https://www.google.com/jsapi"></script>
<script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
<script src="https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script>
<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"></script>

<script type="text/javascript">

  google.load("visualization", "1", {packages:["corechart"]});
  google.setOnLoadCallback(drawChart);

  function drawChart() {
    var data = google.visualization.arrayToDataTable([
      ['Timestamp','TempBMP','TempDHT'],
<?php
#      $sql = "SELECT tmstamp, recordType, tempbmpf, tempdhtf FROM readings WHERE tmstamp >= NOW() - INTERVAL 1 DAY ORDER by tmstamp ASC";
#      $statement = $pdo->query($sql);
#      while ($row = $statement->fetch()) {
      $sql = $pdo->prepare("SELECT tmstamp, recordType, tempbmpf, tempdhtf FROM readings WHERE tmstamp >= NOW() - INTERVAL ? DAY ORDER by tmstamp ASC";
      $sql->execute([$ndays]);
      while ($row = $sql->fetch()) {
        $type = $row['recordType'];
        if ($type == 'LOCAL') {
          echo "['".$row['tmstamp']."',".$row['tempbmpf'].",".$row['tempdhtf']."],";
        }
      }
?>
      ]);

    var options = {
      title: 'Temperature (F) Over Last 24 Hours (BMP: +/- 1.8, DHT: +/- 0.9 degrees)',
      curveType: 'function',
      legend: { position: 'bottom' }
    };

    var chart = new google.visualization.LineChart(document.getElementById("curve_chart"));
    chart.draw(data,options);
  }
 
</script>
<script type="text/javascript">

  google.load("visualization", "1", {packages:["corechart"]});
  google.setOnLoadCallback(drawChart);

  function drawChart() {
    var data = google.visualization.arrayToDataTable([
      ['Date','Humidity'],
<?php
      $sql = "SELECT tmstamp, recordType, humidity FROM readings WHERE tmstamp >= NOW() - INTERVAL 1 DAY ORDER by tmstamp ASC";
      $statement = $pdo->query($sql);
      while ($row = $statement->fetch()) {
        $type = $row['recordType'];
        if ($type == 'LOCAL') {
          echo "['".$row['tmstamp']."',".$row['humidity']."],";
        }
      }
?>
      ]);

    var options = {
      title: 'Humidity Over Last 24 Hours (+/- 2%)',
      curveType: 'function',
      legend: { position: 'bottom' }
    };

    var chart = new google.visualization.LineChart(document.getElementById("curve_chart2"));
    chart.draw(data,options);
  }

</script>
<script type="text/javascript">

  google.load("visualization", "1", {packages:["corechart"]});
  google.setOnLoadCallback(drawChart);

  function drawChart() {
    var data = google.visualization.arrayToDataTable([
      ['Date','Millibars'],
<?php
      $sql = "SELECT tmstamp, recordType, baromB FROM readings WHERE tmstamp >= NOW() - INTERVAL 1 DAY ORDER by tmstamp ASC";
      $statement = $pdo->query($sql);
      while ($row = $statement->fetch()) {
        $type = $row['recordType'];
        if ($type == 'LOCAL') {
          echo "['".$row['tmstamp']."',".$row['baromB']."],";
        }
      }
?>
      ]);

    var options = {
      title: 'Barometer Over Last 24 Hours (+/- 1 mB/hPa)',
      curveType: 'function',
      legend: { position: 'bottom' }
    };

    var chart = new google.visualization.LineChart(document.getElementById("curve_chart3"));
    chart.draw(data,options);
  }

</script>

<body>
 <div id="curve_chart" style="width: 900px; height: 500px"></div>
 <div id="curve_chart3" style="width: 900px; height: 500px"></div>
 <div id="curve_chart2" style="width: 900px; height: 500px"></div>
</body>

</html>

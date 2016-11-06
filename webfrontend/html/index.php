<?php
// LoxBerry DNSmasq-Plugin 
// Christian Woerstenfeld - git@loxberry.woerstenfeld.de
// Version 0.1
// 05.11.2016 16:32:37

// Configuration parameters
$psubdir          =array_pop(array_filter(explode('/',pathinfo($_SERVER["SCRIPT_FILENAME"],PATHINFO_DIRNAME))));
$mydir            =pathinfo($_SERVER["SCRIPT_FILENAME"],PATHINFO_DIRNAME);
$logfile 					=$mydir."/../../../../log/plugins/$psubdir/DNSmasq.log";
$user 						="DNSmasq";
$pass 						="loxberry";

// Enable logging
ini_set("error_log", $logfile);
ini_set("log_errors", 1);

function authenticate()
{
		header("WWW-Authenticate: Basic realm='LoxBerry - DNSmasq-Plugin'");
    header("HTTP/1.0 401 Unauthorized");
		return "\nError, Access denied.\n";
}

// Defaults for inexistent variables
if (!isset($_REQUEST["mode"])) {$_REQUEST["mode"] = 'normal';}

if($_REQUEST["mode"] == "download_logfile")
{
	if (file_exists($logfile)) 
	{
		error_log( date('Y-m-d H:i:s ')."[LOG] Download logfile\n", 3, $logfile);
    header('Content-Description: File Transfer');
    header('Content-Type: text/plain');
    header('Content-Disposition: attachment; filename="'.basename($logfile).'"');
    header('Expires: 0');
    header('Cache-Control: must-revalidate');
    header('Pragma: public');
    header('Content-Length: ' . filesize($logfile));
    readfile($logfile);
	}
	else
	{
		error_log( date('Y-m-d H:i:s ')."Error reading logfile!\n", 3, $logfile);
		die("Error reading logfile."); 
	}
	exit;
}
else if($_REQUEST["mode"] == "show_logfile")
{
	if (file_exists($logfile)) 
	{
		error_log( date('Y-m-d H:i:s ')."[LOG] Show logfile\n", 3, $logfile);
    header('Content-Description: File Transfer');
    header('Content-Type: text/plain');
    header('Content-Disposition: inline; filename="'.basename($logfile).'"');
    header('Expires: 0');
    header('Cache-Control: must-revalidate');
    header('Pragma: public');
    header('Content-Length: ' . filesize($logfile));
    readfile($logfile);
	}
	else
	{
		error_log( date('Y-m-d H:i:s ')."Error reading logfile!\n", 3, $logfile);
		die("Error reading logfile."); 
	}
	exit;
}
else if($_REQUEST["mode"] == "empty_logfile")
{
	if (file_exists($logfile)) 
	{
		if( ( isset($_SERVER['PHP_AUTH_USER'] ) && ( $_SERVER['PHP_AUTH_USER'] == "$user" ) ) AND  ( isset($_SERVER['PHP_AUTH_PW'] ) && ( $_SERVER['PHP_AUTH_PW'] == "$pass" )) )
		{
				$f = @fopen("$logfile", "r+");
				if ($f !== false) 
				{
				    ftruncate($f, 0);
				    fclose($f);
						error_log( date('Y-m-d H:i:s ')."[LOG] Logfile content deleted\n", 3, $logfile);
						$result = "\n<img src='/plugins/$psubdir/DNSMASQ_STATUS_0.png'>";
				}
				else
				{
						error_log( date('Y-m-d H:i:s ')."[LOG] Logfile content not deleted due to problems doing it.\n", 3, $logfile);
						$result = "\n<img src='/plugins/$psubdir/DNSMASQ_STATUS_DOWN.png'>";
				}
		}
		else
		{
				$result = authenticate();
		}
	}
	else
	{
		$result = "\n<img src='/plugins/$psubdir/DNSMASQ_STATUS_DOWN.png'>";
	}
}
else
{
		$result = "Error, invalid request \n";
}

header('Content-Type: text/plain; charset=utf-8');
echo "$result";
exit;

#!/usr/bin/perl

# Copyright 2016-2018 Christian Woerstenfeld, git@loxberry.woerstenfeld.de
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


##########################################################################
# Modules
##########################################################################

use CGI::Carp qw(fatalsToBrowser);
use CGI qw/:standard/;
use Config::Simple '-strict';
use HTML::Entities;
use URI::Escape;
#  use Data::Dumper;
use MIME::Base64 qw( decode_base64 );
use warnings;
use strict;
no  strict "refs"; 
use LoxBerry::System;
use LoxBerry::Web;
use LoxBerry::Log;

##########################################################################
# Variables
##########################################################################
my $logfile 					= "DNSmasq.log";
my $pluginconfigfile 			= $lbpconfigdir."/DNSmasq.cfg";
my $dnsmasqconfigfile			= $lbpconfigdir."/DNSmasq_dnsmasq.cfg";
my $dnsmasqhostsfile 			= $lbpconfigdir."/DNSmasq_hosts.cfg";
my $dnsmasqleasefile 			= $lbpconfigdir."/DNSmasq_leases.cfg";
my $tmp_cfg          			= $lbpconfigdir."/DNSmasq_dnsmasq.tmp";
my $tmp_hosts        			= $lbpconfigdir."/DNSmasq_hosts.tmp";

my $maintemplatefilename 		= "dnsmasq.html";
my $helptemplatefilename		= "help.html";
my $errortemplatefilename 		= "error.html";
my $successtemplatefilename 	= "success.html";
my $error_message				= "";
my $no_error_template_message	= "<b>DNSmasq:</b> The error template is not readable. We must abort here. Please try to reinstall the plugin.";
my $version 					= LoxBerry::System::pluginversion();
my $plugin 						= LoxBerry::System::plugindata();
my $loglevel 					= LoxBerry::System::pluginloglevel();
my $cgi 						= CGI->new;
$LoxBerry::System::DEBUG 		= 1 if $plugin->{PLUGINDB_LOGLEVEL} eq 7;
$LoxBerry::Web::DEBUG 			= 1 if $plugin->{PLUGINDB_LOGLEVEL} eq 7;
$cgi->import_names('R');
%L 								= LoxBerry::System::readlanguage("language.ini");
my $helpurl 					= $L{'HELP.HELPLINK'};
our $template_title				= $L{'ADMIN.MY_NAME'};
my $log 						= LoxBerry::Log->new ( name => 'DNSmasq', filename => $lbplogdir ."/". $logfile, append => 1 );
LOGSTART $L{'LOGGING.ADMIN_CALL'} if $loglevel gt 4;
my $currentlogfile				= $log->filename();
our $do="form";
our $plugin_cfg;
our $namef;
our $value;
our %query;
our $message;
our $handle;
our @dnsmasqconfigfilelines="";
our @dnsmasqhostsfilelines="";
our @dnsmasqleasefilelines="";
our $DNSMASQ_CFG="";
our $DNSMASQ_HOSTS="";
our $DNSMASQ_LEASES="";
our $cfg_stream;
our $hosts_stream;
our $CONTROL_PORT="";
our $DNSMASQ_USE="";
our $SORT_BY_IP="";
our $req;

$R::delete_log if (0);
$R::do if (0);
$do = $R::do if ( $R::do ne "" );
LOGINF $L{'ADMIN.TO_DO'}." ".$do;

if ( $do eq "test" ) 
{
	LOGDEB "Call sub test";
	&get_base_config;
	print "Content-Type: text/plain\n\n";
	&test;
	exit;
}

LOGDEB "Check for delete_log request";
if ( $R::delete_log )
{
	LOGDEB "Found delete_log request, execute deletion in 1 second";
	sleep 1;
	$log->close;
	my $log = LoxBerry::Log->new ( name => 'DNSmasq', filename => $lbplogdir ."/". $logfile, append => 0 );
	LOGSTART $L{'LOGGING.LOG_RESTARTED'};
	print header('text/plain');
	print "OK";
	LOGINF $L{'LOGGING.LOG_RESTARTED'};
	LOGINF $L{'ADMIN.OK_EXIT'};
	exit;
}
else
{
	LOGDEB " No delete_log request, proceed";
}
   
LOGDEB "Check if errortemplate is readable: ".$errortemplatefilename;
stat($lbptemplatedir . "/" . $errortemplatefilename);
if ( !-r _ )
{
	$error_message = $L{'ERRORS.ERR_ERROR_TEMPLATE_NOT_READABLE'};
	LoxBerry::Web::lbheader($template_title, $helpurl, $helptemplatefilename);
	print  $error_message;
	LOGERR $error_message."@".__LINE__;
	LoxBerry::Web::lbfooter();
	LOGINF $L{'ADMIN.ERR_EXIT'};
	exit;
}
else
{
	LOGDEB "Ok, the errortemplate is valid.";
}

LOGDEB "Check if successtemplate is readable: ".$successtemplatefilename;
stat($lbptemplatedir . "/" . $successtemplatefilename);
if ( !-r _ )
{
	LOGDEB "Filename for the successtemplate is not readable, that's bad";
	$error_message = $L{'ERRORS.ERR_SUCCESS_TEMPLATE_NOT_READABLE'};
	&error;
}
else
{
	LOGDEB "Ok, the successtemplate is valid.";
}
LOGDEB "Init successtemplate";
my $successtemplate = HTML::Template->new(
		filename => $lbptemplatedir . "/" . $successtemplatefilename,
		global_vars => 1,
		loop_context_vars => 1,
		die_on_bad_params=> 0,
		associate => $cgi,
		%htmltemplate_options,
		debug => 1,
		);

LOGDEB "Check if maintemplate is readable: ".$maintemplatefilename;
stat($lbptemplatedir . "/" . $maintemplatefilename);
if ( !-r _ )
{
	LOGDEB "Filename for the maintemplate is not readable, that's bad";
	$error_message = $L{'ERRORS.ERR_MAIN_TEMPLATE_NOT_READABLE'};
	&error;
}
else
{
	LOGDEB "Ok, the maintemplate is valid.";
}
LOGDEB "Init maintemplate";
my $maintemplate = HTML::Template->new(
    filename => "$lbptemplatedir/".$maintemplatefilename,
    global_vars => 1,
    loop_context_vars => 1,
    die_on_bad_params => 0
);

LOGDEB "Check if pluginconfigfile is readable: ".$pluginconfigfile;
stat($pluginconfigfile);
if (!-r _ ) 
{
	LOGWARN $L{'ERRORS.ERR_READ_CONFIGFILE'}." (".$pluginconfigfile.") @".__LINE__;
	$error_message = $L{'ERRORS.ERR_CREATE_CONFIG_DIRECTORY'};
	mkdir $lbpconfigdir unless -d $lbpconfigdir or &error; 
	LOGDEB "Try to create a default config";
	$error_message = $L{'ERRORS.ERR_WRITE_CONFIG_FILE'};
	open my $configfileHandle, ">", $pluginconfigfile or &error;
		print $configfileHandle 'CONTROL_PORT="50003"'."\n";
		print $configfileHandle 'DNSMASQ_USE="off"'."\n";
		print $configfileHandle 'SORT_BY_IP="off"'."\n";
	close $configfileHandle;
	$error_message = $L{'ERRORS.ERR_DEFAULT_CONFIG'}." (".$pluginconfigfile.")";
	&error; 
}
else
{
	LOGDEB "pluginconfigfile is readable";
}
LOGDEB "Check if dnsmasqhostsfile is readable: ".$dnsmasqhostsfile;
stat($dnsmasqhostsfile);
if (!-r _ ) 
{
	LOGWARN $L{'ERRORS.ERR_READ_CONFIGFILE'}." (".$dnsmasqhostsfile.") @".__LINE__;
	$error_message = $L{'ERRORS.ERR_CREATE_CONFIG_DIRECTORY'};
	mkdir $lbpconfigdir unless -d $lbpconfigdir or &error; 
	LOGDEB "Try to create a default config";
	$error_message = $L{'ERRORS.ERR_WRITE_CONFIG_FILE'};
	open my $configfileHandle, ">", $dnsmasqhostsfile or &error;
		print $configfileHandle '192.168.178.222 example'."\n";
	close $configfileHandle;
	$error_message = $L{'ERRORS.ERR_DEFAULT_CONFIG'}." (".$dnsmasqhostsfile.")";
	&error; 
}
else
{
	LOGDEB "dnsmasqhostsfile is readable";
}

LOGDEB "Check if dnsmasqconfigfile is readable: ".$dnsmasqconfigfile;
stat($dnsmasqconfigfile);
if (!-r _ ) 
{
	LOGWARN $L{'ERRORS.ERR_READ_CONFIGFILE'}." (".$dnsmasqconfigfile.") @".__LINE__;
	$error_message = $L{'ERRORS.ERR_CREATE_CONFIG_DIRECTORY'};
	mkdir $lbpconfigdir unless -d $lbpconfigdir or &error; 
	LOGDEB "Try to create a default config";
	$error_message = $L{'ERRORS.ERR_WRITE_CONFIG_FILE'};
	open my $configfileHandle, ">", $dnsmasqconfigfile or &error;
		print $configfileHandle 'no-hosts '."\n";
		print $configfileHandle 'no-resolv  '."\n";
		print $configfileHandle 'no-poll'."\n";
		print $configfileHandle 'bogus-priv'."\n";
		print $configfileHandle 'domain-needed'."\n";
		print $configfileHandle 'domain=woersty'."\n";
		print $configfileHandle 'server=192.168.178.1'."\n";
		print $configfileHandle 'local=/localdomain/'."\n";
		print $configfileHandle 'expand-hosts'."\n";
		print $configfileHandle ''."\n";
		print $configfileHandle 'dhcp-range=192.168.178.2,192.168.178.253,30m'."\n";
		print $configfileHandle 'dhcp-option=option:router,192.168.178.1'."\n";
		print $configfileHandle 'dhcp-option=option:ntp-server,130.149.7.7'."\n";
		print $configfileHandle 'dhcp-host=11:22:33:44:55:66,example,30m              #.222'."\n";
		print $configfileHandle '########### FROM HERE IMPORTED FROM /etc/dnsmasq.conf ############'."\n";
		print $configfileHandle '###########  AB HIER IMPORTIERT AUS /etc/dnsmasq.conf ############'."\n";
		close $configfileHandle;
	system("/bin/egrep -v '^#|^\$' /etc/dnsmasq.conf >>".$dnsmasqconfigfile." 2>>".$currentlogfile);
	$error_message = $L{'ERRORS.ERR_DEFAULT_CONFIG'}." (".$dnsmasqconfigfile.")";
	&error; 
}
else
{
	LOGDEB "dnsmasqconfigfile is readable";
}

sub get_base_config
{
LOGINF $L{'ADMIN.READING_CONFIG_FROM'}." ".$pluginconfigfile;
	$plugin_cfg     = new Config::Simple($pluginconfigfile);
	if ( $plugin_cfg )
	{
		$CONTROL_PORT 	= $plugin_cfg->param("default.CONTROL_PORT");
		$DNSMASQ_USE 	= $plugin_cfg->param("default.DNSMASQ_USE");
		$SORT_BY_IP 	= $plugin_cfg->param("default.SORT_BY_IP");
	}
	LOGWARN $L{'ERRORS.ERR_CONFIG_VALUE'}." CONTROL_PORT @".__LINE__ if $CONTROL_PORT lt 1025;
	$CONTROL_PORT = 50003 if $CONTROL_PORT eq "";
	LOGDEB "CONTROL_PORT = $CONTROL_PORT";

	LOGWARN $L{'ERRORS.ERR_CONFIG_VALUE'}." DNSMASQ_USE @".__LINE__ if $DNSMASQ_USE ne 'on' && $DNSMASQ_USE ne 'off';
	$DNSMASQ_USE = "off" if $DNSMASQ_USE ne "on";
	LOGDEB "DNSMASQ_USE = $DNSMASQ_USE";
	
	LOGWARN $L{'ERRORS.ERR_CONFIG_VALUE'}." SORT_BY_IP @".__LINE__ if $SORT_BY_IP ne 'on' && $SORT_BY_IP ne 'off';
	$SORT_BY_IP = "off" if $SORT_BY_IP ne "on";
	LOGDEB "SORT_BY_IP = $SORT_BY_IP";
}
&get_base_config;

LOGDEB "Call sub get_leases" if ($do eq "get_leases");
&get_leases if ($do eq "get_leases");

LOGINF $L{'ADMIN.READING_CONFIG_FROM'}." ".$dnsmasqconfigfile;
  	open $handle, '<', $dnsmasqconfigfile;
  	chomp(@dnsmasqconfigfilelines = <$handle>);
  	close $handle;
  	$DNSMASQ_CFG=join("\n", @dnsmasqconfigfilelines);
	LOGDEB "DNSMASQ_CFG:".$DNSMASQ_CFG;
  
LOGINF $L{'ADMIN.READING_CONFIG_FROM'}." ".$dnsmasqhostsfile;
  	open $handle, '<', $dnsmasqhostsfile;
  	chomp(@dnsmasqhostsfilelines = <$handle>);
  	close $handle;
  	$DNSMASQ_HOSTS=join("\n", @dnsmasqhostsfilelines);
	LOGDEB "DNSMASQ_HOSTS:".$DNSMASQ_HOSTS;
  
LOGDEB "Reading URL datas: ".$ENV{'QUERY_STRING'};
	# Everything from URL
    foreach (split(/&/,$ENV{'QUERY_STRING'}))
    {
      ($namef,$value) = split(/=/,$_,2);
      $namef =~ tr/+/ /;
      $namef =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
      $value =~ tr/+/ /;
      $value =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
      $query{$namef} = $value;
    }
  

   #####################################################
   #
   # Subroutines
   #
   #####################################################

sub get_leases 
{
	LOGINF $L{'ADMIN.FUNCTION_CALLED'}." ".(caller(0))[3]."@".__LINE__;

	   print "Content-Type: text/plain\n\n";
	LOGDEB "Reading DNSmasq Lease file ".$dnsmasqleasefile;
       open $handle, '<', $dnsmasqleasefile or $DNSMASQ_LEASES ="";
       if ($handle)
       {
       chomp(@dnsmasqleasefilelines = <$handle>);
       close $handle;
       }
       $DNSMASQ_LEASES ="";
	LOGDEB "Processing DNSmasq Lease file line by line";
       foreach (sort @dnsmasqleasefilelines)
       {
         my @lines = split (/ /, $_);
         my $remain  = abs(time() - $lines[0]);
         my $dayz    = int($remain/86400);
         my $leftover  = $remain % 86400;
         my $hourz   = int($leftover/3600);
            $leftover  = $leftover % 3600;
         my $minz      = int($leftover/60);
         my $secz      = int($leftover % 60);
         $remain       = sprintf ("%02d:%02d:%02d", $dayz,$hourz,$minz,$secz);
         if ( $dayz > 1 )
         {
           $DNSMASQ_LEASES .= "&gt;23:59:59 &#x2192; ";
         }
         else
         {
           $DNSMASQ_LEASES .= "&nbsp;".$remain." &#x2192; ";
         }
         my ($sec,$min,$hour,$mday,$mon,$year) = (localtime($lines[0]))[0,1,2,3,4,5];
         $DNSMASQ_LEASES .= sprintf ' %02d.%02d.%04d %02d:%02d:%02d ', $mday, $mon+1, $year+1900, $hour, $min, $sec;
         $DNSMASQ_LEASES .= "&#x2190; $_<br/>\n";
       }
       if ($DNSMASQ_LEASES eq "")
       {
   		LOGINF "0 ".$L{'ADMIN.LEASES_FOUND'};
       }
       else
       {
   		LOGINF scalar @dnsmasqleasefilelines." ".$L{'ADMIN.LEASES_FOUND'};
       	}

	   if ($SORT_BY_IP eq "on")
       {
			open(FH, '>', '/tmp/dnsmasqleases') or die $!;
			print FH $DNSMASQ_LEASES;
			close(FH);
			$DNSMASQ_LEASES = `awk '{print \$NF " " \$8,\$0}' /tmp/dnsmasqleases |cut -d" " -f2-|sort  -n -t . -k 1,1 -k 2,2 -k 3,3 -k 4,4|cut -d" " -f2-`;
			unlink('/tmp/dnsmasqleases');
	   }
	   print $DNSMASQ_LEASES;
	   LOGDEB $DNSMASQ_LEASES;
       LOGINF $L{'ADMIN.OK_EXIT'};
       exit;
        
     
 }

if ($do eq "check_config")
{
       LOGDEB "Sub check_config called";
       print "Content-Type: text/plain\n\n";
   
       LOGDEB "Open temporary file: ".$tmp_hosts;
       open($handle, '>', $tmp_hosts) or die "Could not open tempfile '$tmp_hosts' $!";
       print $handle decode_base64( param('hosts_stream') );
       close $handle;
       my @hosts_cfg_data    = split /\n/, decode_base64( param('hosts_stream') );
       my $error_line        = 0;
       foreach (@hosts_cfg_data)
       {
        $error_line = $error_line +1;
 		 LOGDEB "Checking Line ".$error_line." => ".$_;
         my @cur_line = split(/[ \t]+/, $_);
         my $IP = shift @cur_line ;
         if (!($IP =~ /^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$/))
         {
           if ( $IP =~ /^#/ )
           {
             # IP Not OK but Start with # => comment => ignore line
             LOGDEB "Commented out => line ignored";
             next;
           };
           print $L{'ERRORS.ERR_INVALID_IP'}." ".$IP."_gnampf_".$error_line."_gnampf_error_gnampf_HOSTS";
           unlink ($tmp_hosts);
           LOGERR $L{'ERRORS.ERR_INVALID_IP'}." ".$L{'ERRORS.ERR_IN_LINE'}." #".$error_line." => ".$_."@".__LINE__;
           LOGINF $L{'ADMIN.ERR_EXIT'};
           exit;
         }
         else
         {
         	LOGDEB "IP check for line ok";
         }
        
         foreach (@cur_line)
         {
           if (!($_ =~ /^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$/))
           {
	         print $L{'ERRORS.ERR_INVALID_HOSTNAME'}." ".$_."_gnampf_".$error_line."_gnampf_error_gnampf_HOSTS";
             unlink ($tmp_hosts);
             LOGERR $L{'ERRORS.ERR_INVALID_HOSTNAME'}." ".$L{'ERRORS.ERR_IN_LINE'}." #".$error_line." => ".$_."@".__LINE__;
             LOGINF $L{'ADMIN.ERR_EXIT'};
             exit;
           }
           else
           {
           	LOGDEB "HOST check for line ok";
           }
         }
       }
       LOGDEB "Deleting temporary HOST config: ".$tmp_hosts;
       unlink ($tmp_hosts);
   
       # Config
       LOGDEB "Open temporary file: ".$tmp_cfg;
       open($handle, '>', $tmp_cfg) or die "Could not open tempfile '$tmp_cfg' $!";
       print $handle decode_base64( param('cfg_stream') );
       close $handle;
       our $output;
       $output = `/usr/sbin/dnsmasq --test --conf-file=$tmp_cfg --addn-hosts=$tmp_hosts >/dev/stdout 2>&1`;
       if ( $? eq 0 )
       {
       	    LOGINF $L{'ADMIN.CONFIG_CHK_OK'};
       
         unlink ($tmp_cfg) or die "Error deleting tempfile '$tmp_cfg' $!";
         if ( param('save_data') eq 1 )
         {
           LOGINF $L{'ADMIN.SAVE_CONFIG'};
           use Config::Simple '-strict';
           my $temp_controlport=quotemeta(param('CONTROL_PORT'));
           $temp_controlport = $CONTROL_PORT if $temp_controlport eq "";

           my $temp_use        =lc(quotemeta(param('DNSMASQ_USE')));
           $temp_use = $DNSMASQ_USE if $temp_use eq "";

           my $temp_sort       =lc(quotemeta(param('SORT_BY_IP')));
           $temp_sort = $SORT_BY_IP if $temp_sort eq "";

           LOGDEB "temp_controlport: ".$temp_controlport;
           LOGDEB "temp_use: ".$temp_use;
		   LOGDEB "temp_sort: ".$temp_sort;
           $plugin_cfg->param('CONTROL_PORT', $temp_controlport);
           $plugin_cfg->param('DNSMASQ_USE',  $temp_use);
		   $plugin_cfg->param('SORT_BY_IP',  $temp_sort);
           $plugin_cfg->save();
           open($handle, '>', $dnsmasqconfigfile) or die "Could not open '$dnsmasqconfigfile' $!";
           print $handle decode_base64( param('cfg_stream') );
           close $handle;
           open($handle, '>', $dnsmasqhostsfile) or die "Could not open '$dnsmasqhostsfile' $!";
           print $handle decode_base64( param('hosts_stream') );
           close $handle;
   
           if ( $temp_controlport lt 1024 )
           {
             print $L{'ADMIN.TXT_CONTROL_DAEMON_FAILED'}.":<br/><br/><span class='dnsmasq_param_error'>Invalid control port $temp_controlport</span>";
             LOGINF $L{'ADMIN.ERR_EXIT'};
             exit;
           }
           
           LOGINF $L{'ADMIN.OPEN_SOCKET'}." \@TCP".$CONTROL_PORT;
           use IO::Socket::INET;
           # auto-flush on socket
           $| = 1;
   
           # create a connecting socket
           my $socket = new IO::Socket::INET (
           PeerHost => '0.0.0.0',
           PeerPort => "$CONTROL_PORT",
           Proto => 'tcp',
           );
           if ( $socket )
           {
             # data to send to a server
             if ( $temp_controlport ne $CONTROL_PORT )
             {
               # Control Port changed
               $req = 'PoRt_cHaNgEd';
               print "ok";
               LOGINF $L{'ADMIN.SOCKET_SEND'}." ".$req;
               my $size = $socket->send($req);
               shutdown($socket, 1);
               $socket->close();
               LOGINF $L{'ADMIN.OK_EXIT'};
               exit;
             }
   
             if ( $temp_use eq "on" )
             {
               $req = 'ReStArT_DNSmasq';
             }
             else
             {
               $req = 'StOp_DNSmasq';
             }
             LOGINF $L{'ADMIN.SOCKET_SEND'}." ".$req;
             my $size = $socket->send($req);
   
             # notify server that request has been sent
             shutdown($socket, 1);
   
             # receive a response of up to 1024 characters from server
             my $response = "";
             $socket->recv($response, 1024);
             $socket->close();
   
             LOGINF $L{'ADMIN.SOCKET_RECEIVE'}." ".$response;
             if ( $response ne "TXT_CONTROL_DAEMON_OK")
             {
               print $L{'ADMIN.'.$response};
               LOGINF $L{'ADMIN.OK_EXIT'};
               exit;
             }
             else
             {
               print "ok";
               LOGINF $L{'ADMIN.OK_EXIT'};
             }
           }
           else
           {
             print $L{'ADMIN.TXT_CONTROL_DAEMON_FAILED'}.":<br/><br/><span class='dnsmasq_param_error'>".$!."</span><br/><br/><small><i>".$L{'ADMIN.TXT_CONTROL_DAEMON_SUGGEST_REBOOT'}."</i></small>";
   			LOGERR $L{'ADMIN.SOCKET_FAIL'}." => ".$!." @".__LINE__;
			LOGERR $L{'ADMIN.TXT_CONTROL_DAEMON_SUGGEST_REBOOT'};
			LOGINF $L{'ADMIN.ERR_EXIT'};
			exit;
           }
           LOGINF $L{'ADMIN.OK_EXIT'};
           exit;
         }
         else
         {
           LOGINF $L{'ADMIN.NOSAVE_CONFIG'};
           $output = $output ."_gnampf_ok";
         }
       }
       else
       {
       	LOGINF $L{'ADMIN.CONFIG_CHK_FAIL'};
         unlink ($tmp_cfg) or die "Error deleting tempfile '$tmp_cfg' $!";
         $output = $output ."_gnampf_error_gnampf_CFG";
       }
       $output =~ s/\n/\n/g;
       $output =~ s/of $tmp_cfg/ /g;
       $output =~ s/dnsmasq:/ /g;
       $output =~ s/ at line /_gnampf_/g;
       print $output;
       LOGINF $L{'ADMIN.OK_EXIT'};
       exit;
     }
   
   #####################################################
   # Test-Sub to check if DNSmasq Control Server is up
   #####################################################

 sub test
 {
 	LOGINF $L{'ADMIN.FUNCTION_CALLED'}." ".(caller(0))[3]."@".__LINE__;
    LOGINF $L{'ADMIN.OPEN_SOCKET'}." \@TCP".$CONTROL_PORT;
    use IO::Socket::INET;
     # auto-flush on socket
     $| = 1;
     # create a connecting socket
     my $socket = new IO::Socket::INET (
     PeerHost => '0.0.0.0',
     PeerPort => "$CONTROL_PORT",
     Proto => 'tcp',
     );
     if ( $socket )
     {
       # data to send to a server
       $req = 'StAtUs_DNSMASQ';
       LOGINF $L{'ADMIN.SOCKET_SEND'}." ".$req;
       my $size = $socket->send($req);

       # notify server that request has been sent
       shutdown($socket, 1);

       # receive a response of up to 1024 characters from server
       my $response = "";
       $socket->recv($response, 1024);
       $message = $response;

       $socket->close();
       LOGINF $L{'ADMIN.SOCKET_RECEIVE'}." ".$response;
       print $response ;
     }
     else
     {
		LOGERR $L{'ADMIN.SOCKET_FAIL'}." => ".$!." @".__LINE__;
		LOGERR $L{'ADMIN.TXT_CONTROL_DAEMON_SUGGEST_REBOOT'};
		LOGDEB "Set status to: DOWN";
		print "DNSMASQ_STATUS_DOWN" ;
		LOGINF $L{'ADMIN.ERR_EXIT'};
		exit;
     }
   LOGINF $L{'ADMIN.OK_EXIT'};
   exit;
 }
 
   #####################################################
   # Form-Sub
   #####################################################

 sub form
 {
 	LOGINF $L{'ADMIN.FUNCTION_CALLED'}." ".(caller(0))[3]."@".__LINE__;
    LOGINF $L{'ADMIN.SHOW_ADMINPAGE'};
   # The page title read from language file + plugin name
   $template_title = $L{'ADMIN.MY_NAME'};
	# Print Template header
	LoxBerry::Web::lbheader($template_title, $helpurl, $helptemplatefilename);
                                      
	my %MT = LoxBerry::System::readlanguage($maintemplate, "language.ini");
	$maintemplate->param( "LOGO_ICON"		, get_plugin_icon(64));
	$maintemplate->param( "VERSION"			, $version);
	$maintemplate->param( "LOGLEVEL" 		, $L{"LOGGING.LOGLEVEL".$plugin->{PLUGINDB_LOGLEVEL}});
	$maintemplate->param( "LOGLEVEL" 		, "?" ) if ( $plugin->{PLUGINDB_LOGLEVEL} eq "" );
	$maintemplate->param( "LOGFILE" 		, $currentlogfile);
	$maintemplate->param( "LBPPLUGINDIR"	, $lbpplugindir );
	$maintemplate->param( "CONTROL_PORT" 	, $CONTROL_PORT);
	$maintemplate->param( "DNSMASQ_USE" 	, $DNSMASQ_USE);
	$maintemplate->param( "SORT_BY_IP" 		, $SORT_BY_IP);
	$maintemplate->param( "DNSMASQ_HOSTS" 	, $DNSMASQ_HOSTS);
	$maintemplate->param( "DNSMASQ_CFG" 	, $DNSMASQ_CFG);
	print $maintemplate->output();
	LoxBerry::Web::lbfooter();
   LOGINF $L{'ADMIN.OK_EXIT'};
   exit;
 }

   #####################################################
   # Error-Sub
   #####################################################
 
 sub error 
 {
 	LOGINF $L{'ADMIN.FUNCTION_CALLED'}." ".(caller(0))[3]."@".__LINE__;
	LOGDEB "Init errortemplate";
	my $errortemplate = HTML::Template->new(
	filename => $lbptemplatedir . "/" . $errortemplatefilename,
	global_vars => 1,
	loop_context_vars => 1,
	die_on_bad_params=> 0,
	associate => $cgi,
	%htmltemplate_options,
	debug => 1,
	);

 	LOGDEB "Sub error";
 	LOGERR $error_message;
 	LOGDEB "Set page title, load header, parse variables, set footer, end with error";
 	$template_title = $L{'ADMIN.MY_NAME'} . " - " . $L{'ERRORS.ERR_TITLE'};
 	LoxBerry::Web::lbheader($template_title, $helpurl, $helptemplatefilename);
 	$errortemplate->param('ERR_MESSAGE'		, $error_message);
 	$errortemplate->param('ERR_TITLE'		, $L{'ERRORS.ERR_TITLE'});
 	$errortemplate->param('ERR_BUTTON_BACK' , $L{'ERRORS.ERR_BUTTON_BACK'});
 	print $errortemplate->output();
 	LoxBerry::Web::lbfooter();
 	LOGINF $L{'ADMIN.ERR_EXIT'};
 	exit;
 }


&form;

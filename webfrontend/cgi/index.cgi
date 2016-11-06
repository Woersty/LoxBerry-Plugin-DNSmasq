#!/usr/bin/perl

# Copyright 2016 Christian Woerstenfeld, git@loxberry.woerstenfeld.de
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
use Config::Simple;
use File::HomeDir;
use Data::Dumper;
use Cwd 'abs_path';
use HTML::Entities;
use URI::Escape;
use MIME::Base64 qw( decode_base64 );
use warnings;
use strict;
no  strict "refs"; # we need it for template system

##########################################################################
# Variables
##########################################################################
our $cfg;
our $plugin_cfg;
our $phrase;
our $namef;
our $value;
our %query;
our $lang;
our $template_title;
our @help;
our $helptext="";
our $installfolder;
our $languagefile;
our $version;
our $message;
our $nexturl;
our $do="form";
my  $home = File::HomeDir->my_home;
our $psubfolder;
our $languagefileplugin;
our $phraseplugin;
our %Config;
our @config_params;
our $pluginconfigdir;
our $pluginconfigfile;
our @language_strings;
our $wgetbin;
our $error="";
our $handle;
our @dnsmasqconfigfilelines="";
our @dnsmasqhostsfilelines="";
our @dnsmasqleasefilelines="";
our $dnsmasqconfigfile;
our $dnsmasqhostsfile;
our $dnsmasqleasefile;
our $DNSMASQ_CFG="";
our $DNSMASQ_HOSTS="";
our $DNSMASQ_LEASES="";
our $cfg_stream;
our $hosts_stream;
our $tmp_cfg;
our $tmp_hosts;
our $CONTROL_PORT;
our $DNSMASQ_USE;
our $req;

##########################################################################
# Read Settings
##########################################################################


# Version of this script
  $version = "1.0";

# Figure out in which subfolder we are installed
  $psubfolder = abs_path($0);
  $psubfolder =~ s/(.*)\/(.*)\/(.*)$/$2/g;

#Set directories + read LoxBerry config
  $cfg              = new Config::Simple("$home/config/system/general.cfg");
  $installfolder    = $cfg->param("BASE.INSTALLFOLDER");
  $lang             = $cfg->param("BASE.LANG");

#Set directories + read Plugin config
  $pluginconfigdir  = "$home/config/plugins/$psubfolder";
  $pluginconfigfile = "$pluginconfigdir/DNSmasq.cfg";
  $dnsmasqconfigfile= "$pluginconfigdir/DNSmasq_dnsmasq.cfg";
  $dnsmasqhostsfile = "$pluginconfigdir/DNSmasq_hosts.cfg";
  $dnsmasqleasefile = "$pluginconfigdir/DNSmasq_leases.cfg";
  $tmp_cfg          = "$pluginconfigdir/DNSmasq_dnsmasq.tmp";
  $tmp_hosts        = "$pluginconfigdir/DNSmasq_hosts.tmp";

 #Set directories + read Plugin config
  $pluginconfigdir  = "$home/config/plugins/$psubfolder";
  $pluginconfigfile = "$pluginconfigdir/DNSmasq.cfg";
  $plugin_cfg     = new Config::Simple("$pluginconfigfile");
  if ( $plugin_cfg )
  {
    $CONTROL_PORT = $plugin_cfg->param("default.CONTROL_PORT");
    $DNSMASQ_USE = $plugin_cfg->param("default.DNSMASQ_USE");
  }

# Read DNSmasq Config file
open $handle, '<', $dnsmasqconfigfile;
chomp(@dnsmasqconfigfilelines = <$handle>);
close $handle;

$DNSMASQ_CFG=join("\n", @dnsmasqconfigfilelines);

# Read DNSmasq Hosts file
open $handle, '<', $dnsmasqhostsfile;
chomp(@dnsmasqhostsfilelines = <$handle>);
close $handle;

$DNSMASQ_HOSTS=join("\n", @dnsmasqhostsfilelines);

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

# Set parameters coming in - get over post
  if ( !$query{'lang'} )         { if ( param('lang')         ) { $lang         = quotemeta(param('lang'));         } else { $lang         = $lang;  } } else { $lang         = quotemeta($query{'lang'});         }
  if ( !$query{'do'} )           { if ( param('do')           ) { $do           = quotemeta(param('do'));           } else { $do           = "form"; } } else { $do           = quotemeta($query{'do'});           }

# Init Language
# Clean up lang variable
  $lang         =~ tr/a-z//cd;
  $lang         = substr($lang,0,2);
  # If there's no language phrases file for choosed language, use german as default
  if (!-e "$installfolder/templates/system/$lang/language.dat")
  {
    $lang = "de";
  }

# Read translations / phrases
  $languagefile       = "$installfolder/templates/system/$lang/language.dat";
  $phrase             = new Config::Simple($languagefile);
  $languagefileplugin = "$installfolder/templates/plugins/$psubfolder/$lang/language.dat";
  $phraseplugin       = new Config::Simple($languagefileplugin);
  foreach my $key (keys %{ $phraseplugin->vars() } )
  {
    (my $cfg_section,my $cfg_varname) = split(/\./,$key,2);
    push @language_strings, $cfg_varname;
  }
  foreach our $template_string (@language_strings)
  {
    ${$template_string} = $phraseplugin->param($template_string);
  }


##########################################################################
# Main program
##########################################################################

  if ($do eq "get_leases")
  {
    print "Content-Type: text/plain\n\n";
    # Read DNSmasq Lease file
    open $handle, '<', $dnsmasqleasefile or     $DNSMASQ_LEASES ="";
    if ($handle)
    {
    chomp(@dnsmasqleasefilelines = <$handle>);
    close $handle;
    }
    $DNSMASQ_LEASES ="";
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
      $DNSMASQ_LEASES .= "&#x2190; $_<br/>\n"
    }
    if ($DNSMASQ_LEASES eq "")
    {

    }
    print $DNSMASQ_LEASES;
    exit;
  }
  elsif ( $do eq "test")
  {
    print "Content-Type: text/plain\n\n";
    &test;
  }
  elsif ($do eq "check_config")
  {
    print "Content-Type: text/plain\n\n";

    # Hosts
    open($handle, '>', $tmp_hosts) or die "Could not open tempfile '$tmp_hosts' $!";
    print $handle decode_base64( param('hosts_stream') );
    close $handle;
    my @hosts_cfg_data    = split /\n/, decode_base64( param('hosts_stream') );
    my $error_line        = 0;
    foreach (@hosts_cfg_data)
    {
      $error_line = $error_line +1;
      my @cur_line = split(/[ \t]+/, $_);
      my $IP = shift @cur_line ;
      if (!($IP =~ /^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$/))
      {
        if ( $IP =~ /^#/ )
        {
          # IP Not OK but Start with # => comment => ignore line
          next;
        };
        print "Invalid IP '$IP' _gnampf_".$error_line."_gnampf_error_gnampf_HOSTS";
        unlink ($tmp_hosts) or die "Error deleting tempfile '$tmp_hosts' $!";
        exit;
      }
      foreach (@cur_line)
      {
        last if ( $_ =~ /^#/ ); # Start with # => comment => ignore line
        if (!($_ =~ /^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$/))
        {
          print "Invalid Hostname '$_' _gnampf_".$error_line."_gnampf_error_gnampf_CFG";
          unlink ($tmp_hosts) or die "Error deleting tempfile '$tmp_hosts' $!";
          exit;
        }
      }
    }
    unlink ($tmp_hosts) or die "Error deleting tempfile '$tmp_hosts' $!";

    # Config
    open($handle, '>', $tmp_cfg) or die "Could not open tempfile '$tmp_cfg' $!";
    print $handle decode_base64( param('cfg_stream') );
    close $handle;
    our $output;
    $output = `/usr/sbin/dnsmasq --test --conf-file=$tmp_cfg --addn-hosts=$tmp_hosts >/dev/stdout 2>&1`;
    if ( $? eq 0 )
    {
      unlink ($tmp_cfg) or die "Error deleting tempfile '$tmp_cfg' $!";
      if ( param('save_data') eq 1 )
      {
        use Config::Simple '-strict';
        my $temp_controlport=quotemeta(param('CONTROL_PORT'));
        my $temp_use        =lc(quotemeta(param('DNSMASQ_USE')));
        $plugin_cfg->param('CONTROL_PORT', $temp_controlport);
        $plugin_cfg->param('DNSMASQ_USE',  $temp_use);
        $plugin_cfg->save();
        $dnsmasqconfigfile= "$pluginconfigdir/DNSmasq_dnsmasq.cfg";
        $dnsmasqhostsfile = "$pluginconfigdir/DNSmasq_hosts.cfg";
        open($handle, '>', $dnsmasqconfigfile) or die "Could not open '$dnsmasqconfigfile' $!";
        print $handle decode_base64( param('cfg_stream') );
        close $handle;
        open($handle, '>', $dnsmasqhostsfile) or die "Could not open '$dnsmasqhostsfile' $!";
        print $handle decode_base64( param('hosts_stream') );
        close $handle;

        if ( $CONTROL_PORT lt 1024 )
        {
          print $phraseplugin->param("TXT_CONTROL_DAEMON_FAILED").":<br/><br/><span class='dnsmasq_param_error'>Invalid control port $CONTROL_PORT</span>";
          exit;
        }
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
          if ( param('CONTROL_PORT') ne $CONTROL_PORT )
          {
            # Control Port changed
            $req = 'PoRt_cHaNgEd';
            print "ok";
            my $size = $socket->send($req);
            shutdown($socket, 1);
            $socket->close();
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
          my $size = $socket->send($req);

          # notify server that request has been sent
          shutdown($socket, 1);

          # receive a response of up to 1024 characters from server
          my $response = "";
          $socket->recv($response, 1024);
          $socket->close();

          if ( $response ne "TXT_CONTROL_DAEMON_OK")
          {
            print $phraseplugin->param($response);
            exit;
          }
          else
          {
            print "ok";
          }
        }
        else
        {
          print $phraseplugin->param("TXT_CONTROL_DAEMON_FAILED").":<br/><br/><span class='dnsmasq_param_error'>".$!."</span><br/><br/><small><i>".$phraseplugin->param("TXT_CONTROL_DAEMON_SUGGEST_REBOOT")."</i></small>";
          exit;
        }
        exit;
      }
      else
      {
        $output = $output ."_gnampf_ok";
      }
    }
    else
    {
      unlink ($tmp_cfg) or die "Error deleting tempfile '$tmp_cfg' $!";
      $output = $output ."_gnampf_error_gnampf_CFG";
    }
    $output =~ s/\n/\n/g;
    $output =~ s/of $tmp_cfg/ /g;
    $output =~ s/dnsmasq:/ /g;
    $output =~ s/ at line /_gnampf_/g;
    print $output;
    exit;
  }
  else
  {
    print "Content-Type: text/html\n\n";
    &form;
  }
  exit;

#####################################################
#
# Subroutines
#
#####################################################

#####################################################
# Test-Sub to check if DNSmasq Control Server is up
#####################################################

  sub test
  {
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
        my $size = $socket->send($req);

        # notify server that request has been sent
        shutdown($socket, 1);

        # receive a response of up to 1024 characters from server
        my $response = "";
        $socket->recv($response, 1024);
        $message = $response;

        $socket->close();
        print $response ;
      }
      else
      {
        print "DNSMASQ_STATUS_DOWN" ;
      }
    exit;
  }
#####################################################
# Form-Sub
#####################################################

  sub form
  {
    # The page title read from language file + plugin name
    $template_title = $phrase->param("TXT0000") . ": " . $phraseplugin->param("MY_NAME");

    # Print Template header
    &lbheader;

    # Parse the strings we want
    open(F,"$installfolder/templates/plugins/$psubfolder/$lang/settings.html") || die "Missing template plugins/$psubfolder/$lang/settings.html";
    while (<F>)
    {
      $_ =~ s/<!--\$(.*?)-->/${$1}/g;
      print $_;
    }
    close(F);

    # Parse page footer
    &footer;
    exit;
  }

#####################################################
# Error-Sub
#####################################################

  sub error
  {
    $template_title = $phrase->param("TXT0000") . " - " . $phrase->param("TXT0028");

    &lbheader;
    open(F,"$installfolder/templates/system/$lang/error.html") || die "Missing template system/$lang/error.html";
    while (<F>)
    {
      $_ =~ s/<!--\$(.*?)-->/${$1}/g;
      print $_;
    }
    close(F);
    &footer;
    exit;
  }

#####################################################
# Page-Header-Sub
#####################################################

  sub lbheader
  {
     # Create Help page
    open(F,"$installfolder/templates/plugins/$psubfolder/$lang/help.html") || die "Missing template plugins/$psubfolder/$lang/help.html";
      while (<F>)
      {
         $_ =~ s/<!--\$(.*?)-->/${$1}/g;
         $helptext = $helptext . $_;
      }

    close(F);
    open(F,"$installfolder/templates/system/$lang/header.html") || die "Missing template system/$lang/header.html";
      while (<F>)
      {
        $_ =~ s/<!--\$(.*?)-->/${$1}/g;
        print $_;
      }
    close(F);
  }

#####################################################
# Footer
#####################################################

  sub footer
  {
    open(F,"$installfolder/templates/system/$lang/footer.html") || die "Missing template system/$lang/footer.html";
      while (<F>)
      {
        $_ =~ s/<!--\$(.*?)-->/${$1}/g;
        print $_;
      }
    close(F);
  }

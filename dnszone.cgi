#!/usr/bin/perl
# -------------------------------------------------------------------------
# Hamnet IP database - Generate DNS zones
#
# Flori Radlherr, DL8MBT, http://www.radlherr.de
#
# Licensed with Creative Commons Attribution-NonCommercial-ShareAlike 3.0
# http://creativecommons.org/licenses/by-nc-sa/3.0/
# - you may change, distribute and use in non-commecial projects
# - you must leave author and license conditions
# -------------------------------------------------------------------------
#
do "lib.cgi" or die;
#
$ns=   lc $query->param("ns");
$mail= lc $query->param("mail");
$mail= lc $query->param("mail");
$only_as= $query->param("only_as")+0;
$by_as=   $query->param("by_as")+0;
$country= lc $query->param("country");
$suffix=  lc $query->param("suffix");
$by_as= 1 if $only_as>0;
$p_serial= $query->param("serial");

$ns=   "hamnetdb.ampr.org" unless $ns;
$mail= "hostmaster.hamnetdb.net" unless $mail;
$mail=~s/\@/./g;
$suffix= "de.ampr.org" unless $suffix;

$suffix=~s/^\.//;
$suffix=~s/[^a-z0-9\.\-\_]//gi;
$country=~s/[^a-z]//gi;

$newestEdited= 0;

sub zoneHeader {
  my $zone= shift;
  my $as= shift;
  my $serialnr= strftime("%y%m%d%H%M", localtime($newestEdited));

  if ($p_serial) {
    if ($p_serial eq "unix") {
      $serialnr= strftime("%s", localtime($newestEdited));
    }
    else {
      $serialnr= $p_serial;
    }
  }

  $ret= 
    qq(\$ORIGIN .\n).
    qq(\$TTL 10d\n).
    qq($zone. IN SOA $ns. $mail. \(\n).
    qq(    $serialnr ; serial\n).
    qq(    10d        ; refresh\n).
    qq(    1d         ; retry\n).
    qq(    10W        ; expiry\n).
    qq(    1d         ; minimum ttl\n).
    qq(  \)\n\n).
    qq( IN NS $ns.\n);
  
  my $date= strftime("%d.%m.%Y %H:%M:%S", localtime);
  $ret.= "\n";
  $ret.= 
    qq( IN TXT "Generated $date by http://hamnetdb.net v$hamnetdb_version"\n);
  if ($as) {
    $ret.= qq( IN TXT "HAMNET AS $as"\n);
    $ret.= qq( IN TXT "$asSubnetNames{$as}"\n);
  }
  $ret.= "\n";
  $ret.= qq(\$ORIGIN $zone.\n);

  return $ret; 
}

$dirname= "/tmp/hammnetdb_$$";
mkdir($dirname) or &fatal("cannot mkdir $dirname");
chdir($dirname) or &fatal("cannot chdir $dirname");

# read additional zone records for each AS
my $sth= $db->prepare(qq(select as_num,dns_add,country from hamnet_as));
$sth->execute or &fatal("cannot select from hamnet_as");
while (@line= $sth->fetchrow_array) {
  $as_dns_add{$line[0]}= $line[1];
  $as_country{$line[0]}= $line[2];
}


open(CONF, ">named.conf.hamnetdb") or &fatal("cant write named.conf.hamnetdb");
print CONF qq(// Zones-config generated by http://hamnetdb.net\n);

# Read host entries from DB
my $sth= $db->prepare(qq(select ip,name,aliases,rawip,site,
   unix_timestamp(edited) from hamnet_host));
$sth->execute or &fatal("cannot select from hamnet_host");
while (@line= $sth->fetchrow_array) {
  my $idx= 0;
  my $ip= $line[$idx++];
  my $name= $line[$idx++];
  my $aliases= $line[$idx++];
  my $rawip= $line[$idx++];
  my $site= $line[$idx++];
  my $edited= $line[$idx++];

  $namesRaw{"$site:$rawip"}= $name;
  $ipByRaw{$rawip}= $ip;
  $siteByRaw{$rawip}= $site;
  $ipByName{$name}= $ip;
  $editedByRaw{$rawip}= $edited;
  $allSites{$site}= 1;
  $allNames{$name}= 1;

  foreach $alias (split(/[ ,;]+/, $aliases)) {
    $cnames{$ip}{$alias}= 1;
    $allNames{$alias}= 1;
  }
}


# If no "site"-Hostname is present, try CNAME to web.site or router.site
foreach $site (keys %allSites) {
  unless ($allNames{$site}) {
    if ($ipByName{"web.$site"}) {
      $cnames{$ipByName{"web.$site"}}{$site}= 1;
    }
    elsif ($ipByName{"router.$site"}) {
      $cnames{$ipByName{"router.$site"}}{$site}= 1;
    }
    elsif ($ipByName{"hr.$site"}) {
      $cnames{$ipByName{"hr.$site"}}{$site}= 1;
    }
  }
}

# Site names
my $sth= $db->prepare(qq(select callsign,name from hamnet_site));
$sth->execute or &fatal("cannot select from hamnet_site");
while (@line= $sth->fetchrow_array) {
  my $idx= 0;
  my $callsign= $line[$idx++];
  my $name= $line[$idx++];
  $siteName{$callsign}= $name;
}

# Create DHCP range hosts
my $sth= $db->prepare(qq(select ip,begin_ip,end_ip,dhcp_range
         from hamnet_subnet where dhcp_range<>''));
$sth->execute or &fatal("cannot select from hamnet_subnet");
while (@line= $sth->fetchrow_array) {
  my $idx= 0;
  my $ip= $line[$idx++];
  my $begin= $line[$idx++];
  my $end= $line[$idx++];
  my $dhcp_range= $line[$idx++];
  my $lastSite;

  foreach $raw (keys %ipByRaw) {
    if ($raw>=$begin && $raw<$end) {
      $lastSite= $siteByRaw{$raw};
    }
  }

  if ($lastSite && $dhcp_range=~/^(\d+)-(\d+)$/) {
    my $dhcp_begin= $1;
    my $dhcp_end= $2;
    my $netip= $ip;
    $netip=~s/\d+\/\d+//;

    for ($i= $dhcp_begin; $i<=$dhcp_end; $i++) {
      my $ip= $netip.$i;
      my $netipSlash = $netip;
      $netipSlash=~s/\./-/g;
      my $name= "dhcp-$netipSlash$i.$lastSite";
      my $rawip= &aton($ip);

      $namesRaw{"$lastSite:$rawip"}= $name;
      $ipByName{$name}= $ip;
      $ipByRaw{$rawip}= $ip;
      $siteByRaw{$rawip}= $lastSite;
    }
  }
}

# Determine AS for each IP address
my $sth= $db->prepare(qq(select ip,as_parent,begin_ip,end_ip,typ
         from hamnet_subnet
         where typ in ('AS-User/Services','AS-Backbone','AS-Packet-Radio') 
         order by begin_ip));
$sth->execute or &fatal("cannot select from hamnet_subnet");
while (@line= $sth->fetchrow_array) {
  my $idx= 0;
  my $ip= $line[$idx++];
  my $as= $line[$idx++];
  my $begin= $line[$idx++];
  my $end= $line[$idx++];
  my $typ= $line[$idx++];
  $netAs{$ip}= $as;
  my $nt= "bb";
  $nt= "us" if $typ=~/User/i;
  $nt= "pr" if $typ=~/Packet-Radio/;

  if ($only_as) {
    next if $as!=$only_as;
  }
  $typ=~s/AS-//;
  $asSubnetNames{$as}.= ", " if $asSubnetNames{$as};
  $asSubnetNames{$as}.= "$ip $typ";

  foreach $raw (keys %ipByRaw) {
    if ($raw>=$begin && $raw<$end) {
      $hostas{$raw}= $as;
    }
  }
  $allAs{"$as"}= 1;

  my $bits= 0;
  if ($ip=~/^(.*)\/(\d+)$/) {
    $ip= $1;
    $bits= $2;
  }
  if ($bits<=24) {
    my $n= 1<<(24-$bits);
    my $i;
    for ($i= 0; $i<$n; $i++) {
      my $nip= &ntoa(&aton($ip)+256*$i);
      $nip=~s/\.0$//;
      $nets{$nip}= 1;
      $netType{$nip}= $nt;
      $netAs{$nip}= $as;
    }
  }
}

# Generate reverse zones
foreach $net (sort keys %nets) {
  my $name= $net;
  my $lastSite= "";
  my $lastDigit= "x";
  if ($net=~/^(\d+)\.(\d+)\.(\d+)/) {
    $name= "$3.$2.$1.in-addr.arpa";
    $lastDigit= $3;
  }
  elsif ($net=~/^(\d+)\.(\d+)/) {
    $name= "$2.$1.in-addr.arpa";
  }
  elsif ($net=~/^(\d+)/) {
    $name= "$1.in-addr.arpa";
  }

  my $filename= "$name.rev";
  if ($country) {
    $filename= "as$netAs{$net}-$netType{$net}-$lastDigit.$country.rev";
  }
  my $content= "";

  my $subnet= $net;
  $subnet.= ".0/24";
  my $minaddress= &aton("$net.0");
  my $maxaddress= $minaddress+256;

  foreach $key (sort keys %namesRaw) {
    my $rawip= $key;
    $rawip=~s/.*://;
    next if $rawip<$minaddress;
    next if $rawip>$maxaddress;
    next if ($country && $country ne $as_country{$netAs{$net}});
    my $ip= &ntoa($rawip);
    my $as= $hostas{$rawip};
    $newestEdited= $editedByRaw{$rawip} if $editedByRaw{$rawip}>$newestEdited;
    if ($as && $by_as) {
      $as= ".as$as";
    }
    else {
      $as= "";
    }
    if ($siteByRaw{$rawip} ne $lastSite) {
      $lastSite= $siteByRaw{$rawip};
      $content.= "\n; $lastSite - $siteName{$lastSite}\n";
    }
    if ($ip=~/(\d+)\.(\d+)\.(\d+)\.(\d+)/) {
      my $rev= $4;
      $name=~s/:.*//;

      $content.= sprintf("%-7s IN PTR $namesRaw{$key}$as.$suffix.\n", $rev);
    }
  }

  # Write zone if not empty
  if ($content) {
    print CONF qq(\nzone "$name" {\n);
    print CONF qq(  type master;\n);
    print CONF qq(  file "$filename";\n);
    print CONF qq(};\n);

    open(OUT, ">$filename") or &fatal("cant write reverse $filename");
    print OUT &zoneHeader($name, $as);
    print OUT $content;
    close(OUT);
  }
}

if ($by_as) {
  foreach $as (keys %allAs) {
    &createZone($as);
  }
}
else {
  &createZone;
}

# Create one forward zone
sub createZone {
  my $as= shift;
  my $zone= $suffix;
  $zone= "as$as.$suffix" if $as;

  my $filename= "$zone.zone";
  if ($as && $country) {
    $filename= "as$as.$country";
  }
  my $content= "";
  my $lastSite= "";

  $newestEdited= 0;
  foreach $key (sort keys %namesRaw) {
    my $rawip= $key;
    $rawip=~s/.*://;

    if ($country && $as_country{$hostas{$rawip}} ne $country) {
      next;
    }
    if (!$as || ($as eq $hostas{$rawip})) {
      if ($siteByRaw{$rawip} ne $lastSite) {
        $lastSite= $siteByRaw{$rawip};
        $content.= "\n; $lastSite - $siteName{$lastSite}\n";
      }
      my $ip= &ntoa($rawip);
      $content.= sprintf("%-23s IN A $ip\n", $namesRaw{$key});
      $newestEdited= $editedByRaw{$rawip} if $editedByRaw{$rawip}>$newestEdited;

      foreach $cname (keys %{$cnames{$ip}}) {
        unless ($ipByName{$cname}) {
          $content.= sprintf("%-23s IN CNAME $namesRaw{$key}\n", $cname);
        }
      }
    }
  }

  # Write additional records directly into zone
  if ($as && $as_dns_add{$as}) {
    $content.= "\n".$as_dns_add{$as}."\n";
  }

  # Write zone if not empty
  if ($content) {
    print CONF qq(\nzone "$zone" {\n);
    print CONF qq(  type master;\n);
    print CONF qq(  file "$filename";\n);
    print CONF qq(};\n);

    open(OUT, ">$filename") or &fatal("cant write $filename");
    print OUT &zoneHeader($zone, $as);
    print OUT $content;
    close(OUT);
  }
}

# Create tar.gz file with content
$date= strftime("%Y-%m-%d-%H%M", localtime);
print qq(Content-Type: application/x-gtar\n).
 qq(Content-Disposition: attachment; filename=$ns-zones-$date.tgz\n\n);
system("tar zcf - *");
system("rm -rf $dirname");


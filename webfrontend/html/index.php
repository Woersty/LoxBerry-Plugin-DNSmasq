<?php
// LoxBerry DNSmasq-Plugin 
// Christian Woerstenfeld - git@loxberry.woerstenfeld.de
// Version v2018.12.02
// 02.12.2018 22:35:55
// Redirect to Admin page

header("Location: ../../admin/plugins/".array_pop(array_filter(explode('/',pathinfo($_SERVER["SCRIPT_FILENAME"],PATHINFO_DIRNAME)))));
die();

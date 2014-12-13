--
-- Table structure for table `ims_motor_cfg`
--

DROP TABLE IF EXISTS `ims_motor_cfg`;
CREATE TABLE `ims_motor_cfg` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(15) NOT NULL UNIQUE,
  `config` int(11),
  `security` varchar(30),
  `owner` varchar(10),
  `dt_updated` datetime NOT NULL,
  `mutex` varchar(16),
  `FLD_ACCL` double,
  `FLD_BACC` double,
  `FLD_BDST` double,
  `FLD_BS` double,
  `FLD_DIR` varchar(26),
  `FLD_DLVL` smallint(5) unsigned,
  `FLD_EE` varchar(26),
  `FLD_EGAG` varchar(26),
  `FLD_EGU` varchar(40),
  `FLD_EL` double,
  `FLD_ERES` double,
  `FLD_ERSV` varchar(26),
  `FLD_ESKL` double,
  `FLD_FOFF` varchar(26),
  `FLD_FREV` smallint(5) unsigned,
  `FLD_HACC` double,
  `FLD_HC` tinyint(3) unsigned,
  `FLD_HCMX` tinyint(3) unsigned,
  `FLD_HDST` double,
  `FLD_HEGE` varchar(26),
  `FLD_HS` double,
  `FLD_HT` smallint(5) unsigned,
  `FLD_HTYP` varchar(26),
  `FLD_LM` varchar(26),
  `FLD_MODE` varchar(26),
  `FLD_MRES` double,
  `FLD_MT` smallint(5) unsigned,
  `FLD_PDBD` double,
  `FLD_RC` tinyint(3) unsigned,
  `FLD_RCMX` tinyint(3) unsigned,
  `FLD_RDBD` double,
  `FLD_RTRY` tinyint(3) unsigned,
  `FLD_S` double,
  `FLD_SBAS` double,
  `FLD_SF` smallint(5) unsigned,
  `FLD_SM` varchar(26),
  `FLD_SMAX` double,
  `FLD_SREV` int(10) unsigned,
  `FLD_STSV` varchar(26),
  `FLD_TWV` double,
  `FLD_TYPE` varchar(40) NOT NULL UNIQUE,
  `FLD_UREV` double,
  `PV_FW__MEANS` varchar(40),
  `PV_REV__MEANS` varchar(40),
  PRIMARY KEY (`id`),
  index (`config`)
);

--
-- Dumping data for table `ims_motor_cfg`
--

INSERT INTO `ims_motor_cfg` VALUES 
(-1, 'DEFAULT', NULL, NULL, NULL, '2014-11-19 15:50:18', 'VW  ', 1, 1, 0, 1, 'Pos', 0, 'Disable', 'NO', 'mm', 512, NULL, 'MINOR', 1, 'Variable', 200, 1, 0, 0, 5, 'Pos', 1, 500, 'N/A', 'NoDecel, CanHome', 'Normal', NULL, 0, 0.001, 5, 5, 0.0001, 3, 1, 0.1, 200, 'Stop On Stall', 2, 51200, 'MINOR', 0.1, 'DEFAULT', 
1, '+', '-'), 
(1, 'Slit', 0, NULL, 'tst', '2014-12-11 16:44:44', 'VW  ', 0.1, 0.1, 0, 1, 'Neg', 0, 'Enable', 'NO', 'mm', 1000, NULL, 'MINOR', 1, 'Frozen', 200, 1, 5, 5, 5, 'Neg', 2.5, 500, 'E Mark', 'NoDecel, CanHome', 'Normal', NULL, 100, 0.01, 50, 50, 0.0005, 3, 2.5, 0.25, 1000, 'Stop On Stall', 2.5, 51200, 'MINOR', 1, 'slit', 0.4, '', ''), 
(2, 'Slit Horizontal', 1, NULL, 'tst', '2014-11-19 15:54:12', '    ', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'slit_h', NULL, 'Y+', 'Y-'), 
(3, 'Slit Vertical', 1, NULL, 'tst', '2014-11-19 15:54:02', '    ', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'slit_v', NULL, 'X+', 'X-');

/* Sigh. id = 0 in the file does an auto-increment, so we set it to -1 and fix it here. */
update ims_motor_cfg set id = 0 where id = -1;

--
-- Table structure for table `ims_motor_cfg_log`
-- NOTE: This must match ims_motor_cfg, with the addition of date, seq and action and
-- the removal of all uniques and auto_increments!
--

DROP TABLE IF EXISTS `ims_motor_cfg_log`;
CREATE TABLE `ims_motor_cfg_log` (
  `date` datetime,
  `seq` int(31) NOT NULL AUTO_INCREMENT,
  `action` varchar(10) NOT NULL,
  `id` int(11) NOT NULL,
  `name` varchar(45),
  `config` int(11),
  `dt_updated` datetime,
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
  `FLD_UREV` double,
  `FLD_S1` varchar(26),
  `FLD_S2` varchar(26),
  `FLD_S3` varchar(26),
  `FLD_S4` varchar(26),
  `PV_FW__MEANS` varchar(40),
  `PV_REV__MEANS` varchar(40),
  PRIMARY KEY (`seq`),
  INDEX (`id`)
);

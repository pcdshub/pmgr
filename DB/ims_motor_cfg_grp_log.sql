--
-- Table structure for table `ims_motor_cfg_grp`
--

DROP TABLE IF EXISTS `ims_motor_cfg_grp_log`;
CREATE TABLE `ims_motor_cfg_grp_log` (
  `date` datetime,
  `seq` int(31) NOT NULL AUTO_INCREMENT,
  `action` varchar(10) NOT NULL,
  `group_id` int(11) DEFAULT NULL,
  `config_id` int(11) DEFAULT NULL,
  `port_id` int(11) DEFAULT NULL,
  `dispseq` int(11) DEFAULT NULL,
  PRIMARY KEY (`seq`),
  INDEX (`config_id`),
  INDEX (`group_id`),
  INDEX (`port_id`)
);

--
-- Table structure for table `ims_motor_cfg_grp`
--

DROP TABLE IF EXISTS `ims_motor_cfg_grp`;
CREATE TABLE `ims_motor_cfg_grp` (
  `group_id` int(11) DEFAULT NULL,
  `config_id` int(11) DEFAULT NULL,
  `port_id` int(11) DEFAULT NULL,
  `dispseq` int(11) DEFAULT NULL,
  UNIQUE KEY `config_id` (`config_id`,`group_id`),
  KEY `group_id` (`group_id`),
  KEY `port_id` (`port_id`),
  FOREIGN KEY (`config_id`) REFERENCES `ims_motor_cfg` (`id`),
  FOREIGN KEY (`group_id`) REFERENCES `ims_motor_grp` (`id`),
  FOREIGN KEY (`port_id`) REFERENCES `ims_motor` (`id`)
);

--
-- Table structure for table `ims_motor_grp`
--

DROP TABLE IF EXISTS `ims_motor_grp_log`;
CREATE TABLE `ims_motor_grp_log` (
  `date` datetime,
  `seq` int(31) NOT NULL AUTO_INCREMENT,
  `action` varchar(10) NOT NULL,
  `id` int(11) NOT NULL,
  `name` varchar(30) NOT NULL,
  `owner` varchar(10) DEFAULT NULL,
  `dt_created` datetime NOT NULL,
  `dt_updated` datetime NOT NULL,
  PRIMARY KEY (`seq`),
  INDEX (`id`)
);

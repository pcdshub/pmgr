--
-- Table structure for table `ims_motor_grp`
--

DROP TABLE IF EXISTS `ims_motor_grp_log`;
CREATE TABLE `ims_motor_grp_log` (
  `date` datetime,
  `seq` int(31) NOT NULL AUTO_INCREMENT,
  `action` varchar(10) NOT NULL,
  `id` int(11),
  `name` varchar(30),
  `owner` varchar(10),
  `active` tinyint(3),
  `dt_created` datetime,
  `dt_updated` datetime,
  PRIMARY KEY (`seq`),
  INDEX (`id`)
);

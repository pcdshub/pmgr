--
-- Table structure for table `ims_motor_grp`
--

DROP TABLE IF EXISTS `ims_motor_grp`;
CREATE TABLE `ims_motor_grp` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(30) NOT NULL,
  `owner` varchar(10) DEFAULT NULL,
  `dt_created` datetime NOT NULL,
  `dt_updated` datetime NOT NULL,
  PRIMARY KEY (`id`)
);


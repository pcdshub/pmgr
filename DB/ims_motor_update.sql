--
-- Table structure for table `ims_motor_update`
--

DROP TABLE IF EXISTS `ims_motor_update`;
CREATE TABLE `ims_motor_update` (
  `tbl_name` varchar(16) UNIQUE NOT NULL,
  `dt_updated` datetime NOT NULL,
  PRIMARY KEY (`tbl_name`)
);

--
-- Dumping data for table `ims_motor_update`
--

INSERT INTO `ims_motor_update` VALUES ('config','2014-12-12 10:48:32'),('tst','2014-11-19 15:49:12'),('xcs','2014-11-18 13:49:45');

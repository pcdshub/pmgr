--
-- Table structure for table `ims_motor_log`
-- NOTE: This must match ims_motor, with the addition of seq and action and
-- the removal of all uniques and auto_increments!
--

DROP TABLE IF EXISTS `ims_motor_log`;
CREATE TABLE `ims_motor_log` (
  `date` datetime,
  `seq` int(31) NOT NULL AUTO_INCREMENT,
  `action` varchar(10) NOT NULL,
  `id` int(11) NOT NULL,
  `config` int(11),
  `owner` varchar(10),
  `category` varchar(10),
  `rec_base` varchar(40),
  `mutex` varchar(16),
  `dt_created` datetime,
  `dt_updated` datetime,
  `comment`  varchar(80),
  `FLD_SN` varchar(60),
  `FLD_PN` varchar(60),
  PRIMARY KEY (`seq`),
  INDEX (`id`)
);

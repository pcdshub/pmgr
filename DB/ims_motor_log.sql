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
  `name` varchar(30),
  `category` varchar(10),
  `rec_base` varchar(40),
  `mutex` varchar(16),
  `dt_created` datetime,
  `dt_updated` datetime,
  `FLD_DESC` varchar(40),
  `FLD_PORT` varchar(40),
  `FLD_DHLM` double,
  `FLD_DLLM` double,
  `FLD_HLM` double,
  `FLD_HOMD` double,
  `FLD_LLM` double,
  `FLD_OFF` double,
  `FLD_SN` varchar(60),
  `FLD_PN` varchar(60),
  PRIMARY KEY (`seq`),
  INDEX (`id`)
);

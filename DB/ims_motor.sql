--
-- Table structure for table `ims_motor`
--

DROP TABLE IF EXISTS `ims_motor`;
CREATE TABLE `ims_motor` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `config` int(11) NOT NULL,
  `owner` varchar(10),
  `name` varchar(30) NOT NULL UNIQUE,
  `rec_base` varchar(40) NOT NULL,
  `mutex` varchar(16),
  `dt_created` datetime NOT NULL,
  `dt_updated` datetime NOT NULL,
  `FLD_DESC` varchar(40),
  `FLD_PORT` varchar(40),
  `FLD_DHLM` double,
  `FLD_DLLM` double,
  `FLD_HLM` double,
  `FLD_HOMD` double,
  `FLD_LLM` double,
  `FLD_OFF` double,
  PRIMARY KEY (`id`),
  foreign key (config) references ims_motor_cfg(id)
);

--
-- Dumping data for table `ims_motor`
--

INSERT INTO `ims_motor` VALUES 
(1,2,'tst','Test Motor 16','TST:MMS:16','  _`','2014-11-18 14:00:45','2014-11-19 13:52:25','','digi-tst-02:2116',NULL, NULL, 25, 0, -25, 0),
(2,2,'tst','Test Motor 15','TST:MMS:15','  _`','2014-11-18 14:09:07','2014-11-19 13:51:17','','digi-tst-02:2115',NULL, NULL, 25, 0, -25, 0),
(3,3,'tst','Test Motor 14','TST:MMS:14','  _`','2014-11-18 14:09:38','2014-11-19 13:52:25','','digi-tst-02:2114',NULL, NULL, 25, 0, -25, 0),
(4,3,'tst','Test Motor 13','TST:MMS:13','  _`','2014-11-18 14:10:06','2014-11-19 15:49:12','','digi-tst-02:2113',NULL, NULL, 25, 0, -25, 0);

--
-- Table structure for table `ims_motor`
--

DROP TABLE IF EXISTS `ims_motor`;
CREATE TABLE `ims_motor` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `config` int(11) NOT NULL,
  `owner` varchar(10),
  `name` varchar(30) NOT NULL,
  `category` varchar(10),
  `rec_base` varchar(40) NOT NULL,
  `mutex` varchar(16),
  `dt_created` datetime NOT NULL,
  `dt_updated` datetime NOT NULL,
  `comment`  varchar(80),
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
  PRIMARY KEY (`id`),
  foreign key (config) references ims_motor_cfg(id)
);

--
-- Dumping data for table `ims_motor`
--

INSERT INTO `ims_motor` VALUES 
(-1,0,NULL,'DEFAULT','Manual','', '  ab', now(), now(),'','',NULL,NULL, 25, 0, -25, 0, '', '');

/* Sigh. id = 0 in the file does an auto-increment, so we set it to -1 and fix it here. */
update ims_motor set id = 0 where id = -1;

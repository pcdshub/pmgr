--
-- Table structure for table `ims_motor_name_map`
--

DROP TABLE IF EXISTS `ims_motor_name_map`;
CREATE TABLE `ims_motor_name_map` (
  `db_field_name` varchar(30) NOT NULL,
  `alias` varchar(16) NOT NULL,
  `tooltip` varchar(60),
  `enum` varchar(120),
  `col_order` int(11) UNIQUE,
  `set_order` int(11),
  `mutex_mask` int(10) unsigned
);

--
-- Dumping data for table `ims_motor_name_map`
--

INSERT INTO `ims_motor_name_map` VALUES 
('FLD_DESC','DESC',   'Description', '',1,0,0),
('FLD_PORT','PORT',   'digi port address', '',2,0,0),
('FLD_TYPE','TYPE', 'User-defined type', '',3,0,0),
('FLD_LM','LM', 'Limit Stop Mode', 'Invalid|Decel, CanHome|Decel, NoHome|Decel, StopProg|NoDecel, CanHome|NoDecel, NoHome|NoDecel, StopProg',4,0,0),
('FLD_SM','SM', 'stall mode', 'Stop On Stall|No Stop',5,0,0),
('FLD_SF','SF', 'stall factor', '',6,0,0),
('FLD_STSV','STSV', 'stall severity level for reporting', 'NO_ALARM|MINOR|MAJOR|INVALID',7,0,0),
('FLD_ERSV','ERSV', 'Error Severity level for reporting', 'NO_ALARM|MINOR|MAJOR|INVALID',8,0,0),
('FLD_EE','EE', 'Encoder Enabled', 'Disable|Enable',9,0,0),
('FLD_EL','EL', 'Encoder Lines', '',10,0,1),
('FLD_MT','MT', 'Motor Settling Time (ms)', '',11,0,0),
('FLD_HT','HT', 'Holding Current Delay Time (ms)', '',12,0,0),
('FLD_RCMX','RCMX', 'run current max (%: 0..100)', '',13,0,0),
('FLD_RC','RC', 'run current (%: 0..100)', '',14,0,0),
('FLD_HCMX','HCMX', 'Holding current maximum (%: 0..100)', '',15,0,0),
('FLD_HC','HC', 'Holding current (%: 0..100)', '',16,1,0),
('FLD_MODE','MODE', 'Run Mode', 'Normal|Scan',17,0,0),
('FLD_EGU','EGU', 'Engineering Units Name', '',18,0,0),
('FLD_UREV','UREV', 'Units per Revolution (EGU/Rev)', '',19,0,3),
('FLD_FREV','FREV', 'Full Steps per Rev', '',20,0,0),
('FLD_SREV','SREV', 'micro-steps per revolution', '',21,0,0),
('FLD_ERES','ERES', 'Encoder Step Size (EGU)', '',22,0,1),
('FLD_MRES','MRES', 'Motor Resolution (EGU/micro-step)', '',23,0,2),
('FLD_DIR','DIR', 'Direction', 'Pos|Neg',24,0,0),
('FLD_OFF','OFF', 'User Offset', '',25,0,0),
('FLD_FOFF','FOFF', 'Adjust Offset/Controller', 'Variable|Frozen',26,0,0),
('FLD_HTYP','HTYP', 'Homing Type', 'N/A|E Mark|H Switch|Limits|Stall',27,0,0),
('FLD_HEGE','HEGE', 'Homing edge of index or limit', 'Pos|Neg',28,0,0),
('FLD_BDST','BDST', 'Backlash Distance (EGU)', '',29,0,0),
('FLD_HDST','HDST', 'Back-off distance for limit-switch-homing (EGU)', '',30,0,0),
('FLD_DLLM','DLLM', 'Dial Low Limit (EGU)', '',31,0,4),
('FLD_DHLM','DHLM', 'Dial High Limit (EGU)', '',32,0,8),
('FLD_LLM','LLM', 'User Low Limit (EGU)', '',33,0,4),
('FLD_HLM','HLM', 'User High Limit (EGU)', '',34,0,8),
('FLD_RTRY','RTRY', 'Max # of Retries', '',35,0,0),
('FLD_RDBD','RDBD', 'Retry Deadband (EGU)', '',36,0,0),
('FLD_PDBD','PDBD', 'Position Tolerance for monitoring (EGU)', '',37,0,0),
('FLD_SBAS','SBAS', 'base speed (Rev/s)', '',38,0,0),
('FLD_SMAX','SMAX', 'max speed [Rev/s]', '',39,0,0),
('FLD_S','S', 'speed (Rev/s)', '',40,1,0),
('FLD_BS','BS', 'Backlash Speed (EGU/s)', '',41,1,0),
('FLD_HS','HS', 'Home speed (Rev/s)', '',42,1,0),
('FLD_ACCL','ACCL', 'Acceleration (seconds from SBAS to S)', '',43,0,0),
('FLD_BACC','BACC', 'Backlash Accel (seconds from SBAS to S)', '',44,0,0),
('FLD_HACC','HACC', 'Homing Accel (seconds to velocity)', '',45,0,0),
('FLD_TWV','TWV', 'Tweak value (EGU)', '',46,0,0),
('FLD_HOMD','HOMD', 'Dial value at home (EGU)', '',47,0,0),
('FLD_EGAG','EGAG', 'Use External Gauge', 'NO|YES',48,0,0),
('FLD_ESKL','ESKL', 'External Guage Scale', '',49,0,0),
('FLD_DLVL','DLVL', 'Debugging Level', '',50,0,0),
('PV_FW__MEANS','FW_MEANS', 'Name of forward direction', '',51,0,0),
('PV_REV__MEANS','REV_MEANS', 'Name of reverse direction', '',52,0,0);

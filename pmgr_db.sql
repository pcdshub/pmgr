drop table if exists ims_motor_name_map;
drop table if exists ims_motor;
drop table if exists ims_motor_tpl;

create table ims_motor_tpl (
	-- boilerplate --
	pk_ims_motor_tpl int unsigned auto_increment,
	name varchar(15) not null unique, -- name or serial number --
	fk_ims_motor_tpl int unsigned,  -- recursive fk (parent) --
	-- pvs and fields --
	FLD_ACCL  double,  -- Acceleration (seconds from SBAS to S) --
	FLD_BACC  double,  -- Backlash Accel (seconds from SBAS to S) --
	FLD_BDTS  double,  -- Backlash Distance (EGU) --
	FLD_BS    double,  -- Backlash Speed (EGU/s) --
	FLD_DHLM  double,  -- Dial High Limit (EGU) --
	FLD_DIR   varchar(16),  -- Direction [ENUM] --
	FLD_DLLM  double,  -- Dial Low Limit (EGU) --
	FLD_DLVL  smallint unsigned,  -- Debugging Level [DBF_SHORT] --
	FLD_EE    varchar(16),  -- Encoder Enabled [ENUM] -- 
	FLD_EGAG  varchar(16),  -- Use External Gauge [ENUM] --	
	FLD_EGU   varchar(16),  -- Engineering Units Name --
	FLD_EL    double,  -- Encoder Lines --
	FLD_ERBL  varchar(60),  -- External Gauge Readback Link [PV String] --
	FLD_ERBV  double,  -- External Guage RBV --
	FLD_ERES  double,  -- Encoder Step Size (EGU) --
	FLD_ERSV  varchar(16),  -- Error Severity level for reporting [ENUM] --
	FLD_ESKL  double,  -- External Guage Scale --
	FLD_FOFF  varchar(16),  -- Adjust Offset/Controller [ENUM] --
	FLD_FREV  smallint unsigned,  -- Full Steps per Rev --
	FLD_HACC  double,  -- Homing Accel (seconds to velocity) --
	FLD_HC    tinyint unsigned,  -- Holding current (%: 0..100) --
	FLD_HCMX  tinyint unsigned,  -- Holding current maximum (%: 0..100) --
	FLD_HCSV  tinyint unsigned,  -- Holding current last non-zero value (%: 0..100) --
	FLD_HDST  double,  -- Back-off distance for limit-switch-homing (EGU) --
	FLD_HEGE  varchar(16),  -- Homing edge of index or limit [ENUM] --
	FLD_HLM   double,  -- User High Limit (EGU) --
	FLD_HOMD  double,  -- Dial value at home (EGU) --
	FLD_HS    double,  -- Home speed (Rev/s) --
	FLD_HT    smallint unsigned, -- Holding Current Delay Time (ms) --
	FLD_HTYP  varchar(16), -- Homing Type [ENUM] --
	FLD_LLM   double,  -- User High Limit (EGU) --
	FLD_LM    varchar(16), -- Limit Stop Mode [ENUM] --
	FLD_MODE  varchar(16), -- Run Mode [ENUM] --
	FLD_MRES  double,  -- Motor Resolution (EGU/micro-step) --
	FLD_MT    smallint unsigned,  -- Motor Settling Time (ms) --
	FLD_OFF   double,  -- User Offset (EGU) --
	FLD_PDBD  double,  -- Position Tolerance for monitoring (EGU) --
	FLD_RC    tinyint unsigned, -- run current (%: 0..100) --
	FLD_RCMX  tinyint unsigned, -- run current max (%: 0..100) --
	FLD_RDBD  double,  -- Retry Deadband (EGU) --
	FLD_RTRY  tinyint unsigned, -- Max # of Retries --
	FLD_S     double,  -- speed (Rev/s) --
	FLD_SBAS  double,  -- base speed (Rev/s) --
	FLD_SF    smallint unsigned,  -- stall factor --
	FLD_SM 	  varchar(16),  -- stall mode [ENUM] --
	FLD_SMAX  double,  -- max speed [Rev/s] --
	FLD_SREV  int unsigned,  -- micro-steps per revolution --
	FLD_STSV  varchar(16),  -- stall severity level for reporting [ENUM] --
	FLD_TWV   double,  -- Tweak value (EGU) --
	FLD_TYPE  varchar(30) not null unique,
	FLD_UREV  double,  -- Units per Revolution (EGU/Rev) --
	PV_FW__MEANS  varchar(16),  -- Name of forward direction --
	PV_REV__MEANS varchar(16),  -- Name of reverse direction --

	-- constraints --
	primary key (pk_ims_motor_tpl),
	foreign key (fk_ims_motor_tpl) references ims_motor(pk_ims_motor_tpl)
);

create table ims_motor_name_map (
	db_field_name	varchar(30) not null,
	alias		varchar(16) not null,
	displayorder 	int not null,
	py_type 	varchar(16)  -- not sure if this is needed, depends on pyDb Intface --
);

create table ims_motor (
	-- boilerplate --
	pk_ims_motor int auto_increment,
	fk_ims_motor_tpl int,
	name varchar(15) not null,
	rec_base varchar(30) not null,  -- pv/field base prefix --
	dt_created datetime not null,
	dt_updated datetime not null,
	-- pvs and fields --
	FLD_DESC varchar(41),  -- Description --
	FLD_PORT varchar(40),  -- digi port address --	
	
	-- constraints --
	primary key (pk_ims_motor),
	foreign key (fk_ims_motor_tpl) references ims_motor_tpl(pk_ims_motor_tpl)
);
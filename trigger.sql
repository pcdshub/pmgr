use pscontrols;

drop trigger if exists ims_motor_cfg_ins;
drop trigger if exists ims_motor_cfg_del;
drop trigger if exists ims_motor_cfg_upd;
drop trigger if exists ims_motor_ins;
drop trigger if exists ims_motor_del;
drop trigger if exists ims_motor_upd;

delimiter //

create trigger ims_motor_cfg_ins after insert on ims_motor_tpl
for each row
begin
   insert into ims_motor_update values ("config", now())
   on duplicate key update dt_updated = values(dt_updated);
end;
//

create trigger ims_motor_cfg_del after delete on ims_motor_tpl
for each row
begin
   insert into ims_motor_update values ("config", now())
   on duplicate key update dt_updated = values(dt_updated);
end;
//

create trigger ims_motor_cfg_upd after update on ims_motor_tpl
for each row
begin
   insert into ims_motor_update values ("config", now())
   on duplicate key update dt_updated = values(dt_updated);
end;
//

create trigger ims_motor_ins after insert on ims_motor
for each row
begin
   insert into ims_motor_update values (NEW.hutch, now())
   on duplicate key update dt_updated = values(dt_updated);
end;
//

create trigger ims_motor_del after delete on ims_motor
for each row
begin
   insert into ims_motor_update values (OLD.hutch, now())
   on duplicate key update dt_updated = values(dt_updated);
end;
//

create trigger ims_motor_upd after update on ims_motor
for each row
begin
   insert into ims_motor_update values (OLD.hutch, now())
   on duplicate key update dt_updated = values(dt_updated);
   insert into ims_motor_update values (NEW.hutch, now())
   on duplicate key update dt_updated = values(dt_updated);
end;
//

delimiter ;

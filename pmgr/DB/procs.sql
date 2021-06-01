use pscontrols;

drop procedure if exists init_pcds;
drop procedure if exists find_parents;
drop trigger if exists ims_motor_cfg_ins;
drop trigger if exists ims_motor_cfg_del;
drop trigger if exists ims_motor_cfg_upd;
drop trigger if exists ims_motor_ins;
drop trigger if exists ims_motor_del;
drop trigger if exists ims_motor_upd;

delimiter //

create procedure init_pcds()
begin
    create temporary table _ancestors(aid int, level int auto_increment, primary key (level));
end;
//

create procedure find_parents(tableName char(64), inputNo int)
begin
    truncate table _ancestors;
    set @id = inputNo;
    insert into _ancestors values(@id, 0);
    repeat
      set @sql = concat("select config, count(*) into @parent,@y from ", tableName, " where id=@id");
      prepare stmt from @sql;
      execute stmt;
      if @y>0 then
	insert into _ancestors values(@parent, 0);
	set @id=@parent;
      end if;
    until @parent=null or @y=0 end repeat;
    set @sql = concat("select * from _ancestors as a inner join ",
                      tableName, " as t where a.aid = t.id order by level desc");
    prepare stmt from @sql;
    execute stmt;
    truncate table _ancestors;
end;
//

create trigger ims_motor_cfg_ins after insert on ims_motor_cfg
for each row
begin
   insert into ims_motor_update values ("config", now())
   on duplicate key update dt_updated = values(dt_updated);
   insert into ims_motor_cfg_log select now(), 0, 'insert', ims_motor_cfg.* from ims_motor_cfg where id = NEW.id;
end;
//

create trigger ims_motor_cfg_del after delete on ims_motor_cfg
for each row
begin
   insert into ims_motor_update values ("config", now())
   on duplicate key update dt_updated = values(dt_updated);
   insert into ims_motor_cfg_log (date, action, id) values(now(), "delete", OLD.id);
end;
//

create trigger ims_motor_cfg_upd after update on ims_motor_cfg
for each row
begin
   insert into ims_motor_update values ("config", now())
   on duplicate key update dt_updated = values(dt_updated);
   insert into ims_motor_cfg_log select now(), 0, 'update', ims_motor_cfg.* from ims_motor_cfg where id = NEW.id;
end;
//

create trigger ims_motor_ins after insert on ims_motor
for each row
begin
   insert into ims_motor_update values (NEW.owner, now())
   on duplicate key update dt_updated = values(dt_updated);
   insert into ims_motor_log select now(), 0, 'insert', ims_motor.* from ims_motor where id = NEW.id;
end;
//

create trigger ims_motor_del after delete on ims_motor
for each row
begin
   insert into ims_motor_update values (OLD.owner, now())
   on duplicate key update dt_updated = values(dt_updated);
   insert into ims_motor_log (date, action, id) values(now(), "delete", OLD.id);
end;
//

create trigger ims_motor_upd after update on ims_motor
for each row
begin
   insert into ims_motor_update values (OLD.owner, now())
   on duplicate key update dt_updated = values(dt_updated);
   insert into ims_motor_update values (NEW.owner, now())
   on duplicate key update dt_updated = values(dt_updated);
   insert into ims_motor_log select now(), 0, 'update', ims_motor.* from ims_motor where id = NEW.id;
end;
//

delimiter ;

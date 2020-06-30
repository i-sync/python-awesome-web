-- schema.sql

drop database if exists awesome_blog;

create database awesome_blog;

use awesome_blog;

-- grant select, insert, update, delete on awesome.* to 'www-data'@'localhost' identified by 'www-data';

create table users (
    `id` varchar(50) not null,
    `email` varchar(50) not null,
    `password` varchar(50) not null,
    `admin` bool not null,
    `name` varchar(50) not null,
    `image` varchar(500) not null,
    `created_at` real not null,
    unique key `idx_email` (`email`),
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;

create table blogs (
    `id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `name` varchar(500) not null,
    `summary` varchar(2048) not null,
    `content` mediumtext not null,
    `category_id` varchar(50),
    `category_name` varchar(50),
    `view_count` int unsigned not null,
    `created_at` real not null,
    `enabled` boolean,
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;

create table comments (
    `id` varchar(50) not null,
    `blog_id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `content` mediumtext not null,
    `created_at` real not null,
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;

create table comments_anonymous(
    `id` varchar(50) not null,
    `parent_id` varchar(50),
    `blog_id` varchar(50) not null,
    `target_name` varchar(50),
    `content` mediumtext not null,
    `name` varchar(50) not null,
    `email` varchar(50),
    `website` varchar(100),
    `avatar` varchar(200),
    `ip` varchar(50),
    `created_at` real not null,
    key `idx_created_at` (`created_at`),
    primary key(`id`)
) engine=innodb default charset=utf8;

create table categories(
  `id` varchar (50) not null,
  `name` varchar(50) not null,
  `created_at` real not null,
  key `idx_created_at` (`created_at`),
  primary key (`id`)
) engine=innodb default charset=utf8;
-- --------------------------------------------------------
-- Host:                         127.0.0.1
-- Server version:               8.4.4 - MySQL Community Server - GPL
-- Server OS:                    Win64
-- HeidiSQL Version:             12.10.0.7000
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Dumping database structure for factory
CREATE DATABASE IF NOT EXISTS `factory` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `factory`;

-- Dumping structure for table factory.fingerprint
CREATE TABLE IF NOT EXISTS `fingerprint` (
  `idx` int NOT NULL AUTO_INCREMENT,
  `uuid` varchar(50) DEFAULT NULL,
  `model_id` varchar(50) DEFAULT NULL,
  `timestamp` timestamp(6) NOT NULL,
  `anomaly_score` float DEFAULT NULL,
  `remark` text,
  PRIMARY KEY (`idx`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table factory.mtc_condition
CREATE TABLE IF NOT EXISTS `mtc_condition` (
  `idx` int NOT NULL AUTO_INCREMENT,
  `dataItemId` varchar(30) NOT NULL,
  `uuid` varchar(30) NOT NULL,
  `tag` varchar(45) NOT NULL,
  `timestamp` timestamp(6) NOT NULL,
  `type` varchar(45) DEFAULT NULL,
  `value` varchar(45) DEFAULT NULL,
  `avail` varchar(20) DEFAULT NULL,
  `nativeCode` varchar(45) DEFAULT NULL,
  `nativeSeverity` varchar(45) DEFAULT NULL,
  `qualifier` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`idx`),
  KEY `timestamp` (`timestamp`)
) ENGINE=InnoDB AUTO_INCREMENT=49236 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table factory.mtc_dataitem
CREATE TABLE IF NOT EXISTS `mtc_dataitem` (
  `id` varchar(30) NOT NULL,
  `uuid` varchar(30) NOT NULL,
  `component` varchar(45) DEFAULT NULL,
  `category` varchar(20) DEFAULT NULL,
  `type` varchar(30) DEFAULT NULL,
  `representation` varchar(20) DEFAULT NULL,
  `subtype` varchar(20) DEFAULT NULL,
  `name` varchar(45) DEFAULT NULL,
  `units` varchar(20) DEFAULT NULL,
  `nativeUnits` varchar(20) DEFAULT NULL,
  `coordinateSystem` varchar(20) DEFAULT NULL,
  `statistic` varchar(20) DEFAULT NULL,
  `significantDigits` varchar(20) DEFAULT NULL,
  `sampleRate` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`,`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table factory.mtc_device
CREATE TABLE IF NOT EXISTS `mtc_device` (
  `uuid` varchar(30) NOT NULL,
  `id` varchar(20) DEFAULT NULL,
  `name` varchar(20) DEFAULT NULL,
  `version` varchar(45) DEFAULT NULL,
  `mtconnect_schema` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table factory.mtc_event
CREATE TABLE IF NOT EXISTS `mtc_event` (
  `idx` int unsigned NOT NULL AUTO_INCREMENT,
  `dataitemId` varchar(30) NOT NULL,
  `uuid` varchar(30) NOT NULL,
  `tag` varchar(45) DEFAULT NULL,
  `timestamp` timestamp(6) NOT NULL,
  `value` text,
  `avail` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`idx`),
  KEY `timestamp` (`timestamp`)
) ENGINE=InnoDB AUTO_INCREMENT=9239830 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table factory.mtc_instance
CREATE TABLE IF NOT EXISTS `mtc_instance` (
  `uuid` varchar(30) NOT NULL,
  `instanceId` int unsigned NOT NULL DEFAULT '0',
  `latest_sequence` int unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`uuid`,`instanceId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table factory.mtc_sample
CREATE TABLE IF NOT EXISTS `mtc_sample` (
  `idx` int unsigned NOT NULL AUTO_INCREMENT,
  `dataItemId` varchar(20) NOT NULL,
  `uuid` varchar(30) NOT NULL,
  `tag` varchar(45) DEFAULT NULL,
  `timestamp` timestamp(6) NOT NULL,
  `value` float DEFAULT NULL,
  `avail` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`idx`),
  KEY `timestamp` (`timestamp`)
) ENGINE=InnoDB AUTO_INCREMENT=87105276 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table factory.operation
CREATE TABLE IF NOT EXISTS `operation` (
  `idx` int NOT NULL AUTO_INCREMENT,
  `uuid` varchar(30) DEFAULT NULL,
  `part` varchar(45) NOT NULL,
  `start_timestamp` timestamp(6) NOT NULL,
  `end_timestamp` timestamp(6) NULL DEFAULT NULL,
  `remark` text,
  `tool_idx` int DEFAULT NULL,
  PRIMARY KEY (`idx`),
  UNIQUE KEY `start_timestamp` (`start_timestamp`)
) ENGINE=InnoDB AUTO_INCREMENT=3268 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table factory.sound_data
CREATE TABLE IF NOT EXISTS `sound_data` (
  `idx` int NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`idx`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table factory.tool_order
CREATE TABLE IF NOT EXISTS `tool_order` (
  `idx` int NOT NULL AUTO_INCREMENT,
  `uuid` varchar(45) NOT NULL,
  `part` varchar(20) DEFAULT NULL,
  `tool_order` varchar(60) NOT NULL,
  `is_Active` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`idx`),
  UNIQUE KEY `tool_order_UNIQUE` (`tool_order`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;

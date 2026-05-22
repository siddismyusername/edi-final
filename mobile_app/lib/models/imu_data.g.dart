// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'imu_data.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ImuData _$ImuDataFromJson(Map<String, dynamic> json) => ImuData(
      timestamp: (json['timestamp'] as num).toDouble(),
      ax: (json['ax'] as num).toDouble(),
      ay: (json['ay'] as num).toDouble(),
      az: (json['az'] as num).toDouble(),
      gx: (json['gx'] as num).toDouble(),
      gy: (json['gy'] as num).toDouble(),
      gz: (json['gz'] as num).toDouble(),
    );

Map<String, dynamic> _$ImuDataToJson(ImuData instance) => <String, dynamic>{
      'timestamp': instance.timestamp,
      'ax': instance.ax,
      'ay': instance.ay,
      'az': instance.az,
      'gx': instance.gx,
      'gy': instance.gy,
      'gz': instance.gz,
    };

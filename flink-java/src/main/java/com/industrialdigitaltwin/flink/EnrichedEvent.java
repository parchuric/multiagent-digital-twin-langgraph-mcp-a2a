package com.industrialdigitaltwin.flink;

public class EnrichedEvent {
    public String scadaId;
    public String gpsId;
    public String deviceId;
    public String timestamp;
    public double value;
    public double latitude;
    public double longitude;
    // Add more fields as needed

    public EnrichedEvent() {}
}

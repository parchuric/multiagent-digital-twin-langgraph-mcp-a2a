package com.industrialdigitaltwin.flink;

import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.functions.MapFunction;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import com.fasterxml.jackson.databind.ObjectMapper;

// Azure Identity for AD Auth
import com.azure.identity.DefaultAzureCredentialBuilder;

// Cosmos DB imports
import org.apache.flink.connector.cosmos.sink.CosmosDBSink;
import org.apache.flink.connector.cosmos.sink.config.CosmosDBConfig;
import org.apache.flink.api.common.eventtime.SerializableTimestampAssigner;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.apache.flink.streaming.api.datastream.SingleOutputStreamOperator;
import org.apache.flink.streaming.api.datastream.KeyedStream;
import org.apache.flink.streaming.api.datastream.JoinedStreams;
import org.apache.flink.streaming.api.functions.co.ProcessJoinFunction;
import org.apache.flink.util.Collector;

public class StreamingJob {

    private static final ObjectMapper objectMapper = new ObjectMapper();

    public static void main(String[] args) throws Exception {
        final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // --- KAFKA SOURCE --- //
        String kafkaBootstrapServers = System.getenv("KAFKA_BOOTSTRAP_SERVERS");
        String kafkaTopic = System.getenv("KAFKA_TOPIC");

        if (kafkaBootstrapServers == null || kafkaTopic == null) {
            System.err.println("Please set KAFKA_BOOTSTRAP_SERVERS and KAFKA_TOPIC environment variables.");
            System.exit(1);
        }

        KafkaSource<String> source = KafkaSource.<String>builder()
                .setBootstrapServers(kafkaBootstrapServers)
                .setTopics(kafkaTopic)
                .setGroupId("flink-consumer-group")
                .setStartingOffsets(OffsetsInitializer.latest())
                .setValueOnlyDeserializer(new SimpleStringSchema())
                .build();

        DataStream<String> kafkaStream = env.fromSource(source, WatermarkStrategy.noWatermarks(), "Kafka Source");

        // --- DATA TRANSFORMATION --- //
        // Deserialize JSON strings into ScadaEvent objects
        DataStream<ScadaEvent> scadaEvents = kafkaStream.map(new MapFunction<String, ScadaEvent>() {
            @Override
            public ScadaEvent map(String value) throws Exception {
                return objectMapper.readValue(value, ScadaEvent.class);
            }
        });

        // --- SECOND KAFKA SOURCE FOR GPS EVENTS --- //
        String gpsKafkaTopic = System.getenv("KAFKA_GPS_TOPIC");
        if (gpsKafkaTopic == null) {
            System.err.println("Please set KAFKA_GPS_TOPIC environment variable.");
            System.exit(1);
        }
        KafkaSource<String> gpsSource = KafkaSource.<String>builder()
                .setBootstrapServers(kafkaBootstrapServers)
                .setTopics(gpsKafkaTopic)
                .setGroupId("flink-gps-consumer-group")
                .setStartingOffsets(OffsetsInitializer.latest())
                .setValueOnlyDeserializer(new SimpleStringSchema())
                .build();
        DataStream<String> gpsKafkaStream = env.fromSource(gpsSource, WatermarkStrategy.noWatermarks(), "Kafka GPS Source");
        DataStream<GpsEvent> gpsEvents = gpsKafkaStream.map(new MapFunction<String, GpsEvent>() {
            @Override
            public GpsEvent map(String value) throws Exception {
                return objectMapper.readValue(value, GpsEvent.class);
            }
        });

        // --- ASSIGN TIMESTAMPS & WATERMARKS --- //
        SingleOutputStreamOperator<ScadaEvent> scadaWithTimestamps = scadaEvents.assignTimestampsAndWatermarks(
            WatermarkStrategy.<ScadaEvent>forMonotonousTimestamps()
                .withTimestampAssigner(new SerializableTimestampAssigner<ScadaEvent>() {
                    @Override
                    public long extractTimestamp(ScadaEvent event, long recordTimestamp) {
                        return javax.xml.bind.DatatypeConverter.parseDateTime(event.timestamp).getTimeInMillis();
                    }
                })
        );
        SingleOutputStreamOperator<GpsEvent> gpsWithTimestamps = gpsEvents.assignTimestampsAndWatermarks(
            WatermarkStrategy.<GpsEvent>forMonotonousTimestamps()
                .withTimestampAssigner(new SerializableTimestampAssigner<GpsEvent>() {
                    @Override
                    public long extractTimestamp(GpsEvent event, long recordTimestamp) {
                        return javax.xml.bind.DatatypeConverter.parseDateTime(event.timestamp).getTimeInMillis();
                    }
                })
        );

        // --- KEY BY DEVICE/UNIT ID --- //
        KeyedStream<ScadaEvent, String> keyedScada = scadaWithTimestamps.keyBy(e -> e.a_id);
        KeyedStream<GpsEvent, String> keyedGps = gpsWithTimestamps.keyBy(e -> e.unit_id);

        // --- CROSS-STREAM INTERVAL JOIN (SCADA + GPS) --- //
        DataStream<EnrichedEvent> joined = keyedScada
            .intervalJoin(keyedGps)
            .between(Time.seconds(-30), Time.seconds(30)) // join within +/-30s window
            .process(new ProcessJoinFunction<ScadaEvent, GpsEvent, EnrichedEvent>() {
                @Override
                public void processElement(ScadaEvent scada, GpsEvent gps, Context ctx, Collector<EnrichedEvent> out) {
                    EnrichedEvent enriched = new EnrichedEvent();
                    enriched.scadaId = scada.id;
                    enriched.gpsId = gps.id;
                    enriched.deviceId = scada.a_id;
                    enriched.timestamp = scada.timestamp;
                    enriched.value = scada.value;
                    enriched.latitude = gps.latitude;
                    enriched.longitude = gps.longitude;
                    out.collect(enriched);
                }
            });

        // --- STATEFUL WINDOWED AGGREGATION (MOVING AVERAGE) --- //
        DataStream<DeviceAvg> movingAvg = keyedScada
            .timeWindow(Time.minutes(5), Time.minutes(1))
            .aggregate(new MovingAverageAggregate());

        // --- COSMOS DB SINK --- //
        String cosmosDbEndpoint = System.getenv("COSMOS_DB_ENDPOINT");
        String cosmosDbDatabase = System.getenv("COSMOS_DB_DATABASE");
        String cosmosDbContainer = System.getenv("COSMOS_DB_CONTAINER");

        if (cosmosDbEndpoint == null || cosmosDbDatabase == null || cosmosDbContainer == null) {
            System.err.println("Please set COSMOS_DB_ENDPOINT, COSMOS_DB_DATABASE, and COSMOS_DB_CONTAINER environment variables.");
            System.exit(1);
        }

        CosmosDBConfig cosmosDBConfig = CosmosDBConfig.builder()
            .setEndpoint(cosmosDbEndpoint)
            .setCredential(new DefaultAzureCredentialBuilder().build())
            .setDatabase(cosmosDbDatabase)
            .setContainer(cosmosDbContainer)
            .build();

        CosmosDBSink<ScadaEvent> cosmosSink = CosmosDBSink.<ScadaEvent>builder()
            .setCosmosDBConfig(cosmosDBConfig)
            .build();

        // Add the sink to the stream
        scadaEvents.sinkTo(cosmosSink);

        // --- SINKS (EXAMPLE: PRINT TO LOG) --- //
        joined.print("Joined SCADA+GPS");
        movingAvg.print("MovingAvg");

        env.execute("Industrial Digital Twin Flink Job");
    }
}

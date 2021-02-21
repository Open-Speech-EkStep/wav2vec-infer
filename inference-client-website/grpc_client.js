const grpc = require("grpc");

function GrpcClient(host) {
    const PROTO_PATH =
        __dirname +
        (process.env.PROTO_PATH || "/audio_to_text.proto");
    const protoLoader = require("@grpc/proto-loader");

    let packageDefinition = protoLoader.loadSync(PROTO_PATH, {
        keepCase: true,
        longs: String,
        enums: String,
        defaults: true,
        oneofs: true,
    });
    let proto = grpc.loadPackageDefinition(packageDefinition).recognize;
    this.host = host;
    let grpcClient = new proto.Recognize(
        host,
        grpc.credentials.createInsecure()
    );

    this.recognizeAudio = ()=>{
        return grpcClient.recognize_audio();
    }

    this.close = () => {
        grpc.closeClient(grpcClient);
    }
    return this;
};

module.exports = GrpcClient;
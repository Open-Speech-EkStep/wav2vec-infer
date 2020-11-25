"use strict";

const grpc = require("grpc");
var express = require("express");
const app = express();
const server = require("http").createServer(app);
const io = require("socket.io")(server);
const path = require("path");

app.use(express.static(path.join(__dirname, "static")));

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

function make_message(message, audio, id, mic_flag = "continue", language = 'en') {
  const msg = {
    message: message,
    audio: audio,
    user: String(id),
    mic_flag: mic_flag,
    language: language
  };
  return msg;
}

function main() {
  let client = new proto.Recognize(
    "localhost:55102",
    grpc.credentials.createInsecure()
  );
  let call = client.recognize_audio();

  let clientBuffers = {};
  let idDict = {};
  let clientTranscription = {};
  io.on("connection", (socket) => {
    socket.on("start", function (response) {
      delete clientBuffers[socket.id];
      delete idDict[socket.id];
      delete clientTranscription[socket.id];
    });

    socket.on("end", function (response) {
      delete clientBuffers[socket.id];
    });

    socket.on("disconnect", () => {
      delete clientBuffers[socket.id];
      delete idDict[socket.id];
      delete clientTranscription[socket.id];
    });

    socket.on("mic_data", function (chunk, speaking, language='en') {
      let mic_flag = "replace", sid = socket.id;
      if(!clientBuffers[sid]){
        clientBuffers[sid] = chunk;
      }else{
        clientBuffers[sid] = Buffer.concat([
          clientBuffers[sid],
          chunk,
        ]);
      }
      let buffer = clientBuffers[sid];
      if(!speaking /*|| clientBuffers[socket.id].length >= 102400*/){
        delete clientBuffers[sid];
        mic_flag = "append";
      }
      const msg = make_message(
        "mic",
        buffer,
        sid,
        mic_flag,
        language
      );
      call.write(msg);
    });

    socket.on("file_data", function (chunk, language='en') {
      let mic_flag = "append";
      const msg = make_message(
        "file",
        chunk,
        socket.id,
        mic_flag,
        language
      );
      call.write(msg);
    });

    call.on("data", function (response) {
      const message = JSON.parse(response.message);
      const id = message["id"];
      const user = response.user;
      if (idDict[user] && idDict[user] === id) {
        return;
      } else {
        idDict[user] = id;
      }
      if(!message["success"]){
        return;
      }
      if (response.type === "file") {
        io.to(response.user).emit("file_upload_response", message["transcription"]);
      } else {
        if(!clientTranscription[user])clientTranscription[user] = "";
        let transcription = clientTranscription[user]+" "+message["transcription"]
        if (response.mic_flag === "append") {
          clientTranscription[user] = transcription;
        }
        io.to(response.user).emit("response", transcription);
      }
    });
  });

  app.get("/", function (req, res) {
    res.sendFile("index.html", { root: __dirname });
  });
  const PORT = 9009;
  server.listen(PORT);
  console.log("Listening in port => " + PORT);
}

main();

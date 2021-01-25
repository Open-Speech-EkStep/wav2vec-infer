"use strict";
require('dotenv').config();
const grpc = require("grpc");
var express = require("express");
const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const server = require("http").createServer(app);
const io = require("socket.io")(server);
const path = require("path");
const fs = require("fs");
const { addFeedback, getFeedback } = require('./dbOperations');
app.use(express.static(path.join(__dirname, "static")));

const { uploadFile } = require('./uploader');
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
const idDict = {};
const userCalls = {};

function make_message(audio, user, speaking, language = 'en') {
  const msg = {
    audio: audio,
    user: user + "",
    language: language,
    speaking: speaking
  };
  return msg;
}

function onResponse(response) {
  // console.log(response)
  const data = JSON.parse(response.transcription);
  const id = data["id"];
  const user = response.user;
  if (idDict[user] && idDict[user] === id) {
    return;
  } else {
    idDict[user] = id;
  }
  if (!data["success"]) {
    return;
  }
  io.to(response.user).emit("response", data["transcription"], response.language);
}

function onUserConnected(socket, grpc_client) {
  userCalls[socket.id] = grpc_client.recognize_audio();
  userCalls[socket.id].on("data", onResponse);
  io.to(socket.id).emit("id", socket.id);
}

function startServer() {
  const currentDateAndTime = () => {
    return new Date().toISOString().replace(/[-:T.]/g, '');
  };
  const randomString = () => {
    return (Math.random() + 1).toString(36).substring(2, 10);
  };
  const multer = require('multer');
  const multerStorage = multer.diskStorage({
    destination: function (req, file, cb) {
      if (!fs.existsSync('uploads')) {
        fs.mkdirSync('uploads');
        console.log('Created directory uploads');
      }
      cb(null, 'uploads/');
    },
    filename: function (req, file, cb) {
      cb(null, currentDateAndTime() + '_' + randomString() + '.wav');
    },
  });
  const upload = multer({ storage: multerStorage });
  app.use(upload.single('audio_data'));
  app.get("/", function (req, res) {
    res.sendFile("index.html", { root: __dirname });
  });

  app.get("/feedback", function (req, res) {
    res.sendFile("feedback.html", { root: __dirname });
  });

  app.post("/api/feedback", function (req, res) {
    const file = req.file;
    const { user_id, language, text, rating, device } = req.body;

    uploadFile(file.path, user_id, language)
      .then((uploadResponse) => {
        console.log("responsed")
        const blobName = uploadResponse[0]['metadata']['name'];
        const bucketName = uploadResponse[0]['metadata']['bucket'];
        const audio_path = `https://storage.googleapis.com/${bucketName}/${blobName}`
        addFeedback(user_id, language, audio_path, text, rating, device).then(() => {
          res.json({ "success": true })
        }).catch(err => {
          console.log("error", err)
          res.status(500).json({ "success": false })
        })
      })
      .catch((err) => {
        console.error("error", err);
        res.sendStatus(500);
      })
      .finally(() => {
        fs.unlink(file.path, function (err) {
          if (err) {
            console.log(`File ${file.path} not deleted!`);
            console.log(err);
          }
        });
      });
  })

  app.get("/api/feedback", function (req, res) {
    const start = Number(req.query.start) || 0;
    const size = Number(req.query.length) || 10;
    const ratingFilter = req.query.rating_filter || '';
    const deviceFilter = req.query.device_filter || '';
    getFeedback(start, size, ratingFilter, deviceFilter).then(result => {
      res.json({
        "draw": req.query.draw | 1,
        "recordsTotal": result['total'],
        "recordsFiltered": result['filtered'],
        "data": result['data']
      })
    }).catch(err => {
      if (err.name && err.name == 'QueryResultError') {
        res.json({
          "draw": req.query.draw | 1,
          "recordsTotal": 0,
          "recordsFiltered": 0,
          "data": []
        })
      } else {
        res.status(500).json({ "success": false })
      }
    })
  })

  const PORT = 9008;
  server.listen(PORT);
  console.log("Listening in port => " + PORT);
}

function main() {

  let grpc_client = new proto.Recognize(
    "localhost:55102",
    grpc.credentials.createInsecure()
  );

  io.on("connection", (socket) => {
    onUserConnected(socket, grpc_client);

    socket.on("start", function () {
      grpc_client.start({ 'user': "" + socket.id }, function (err, resp) {

      })
    });

    socket.on("end", function () {
      grpc_client.end({ 'user': "" + socket.id }, function (err, resp) {

      })
    });

    socket.on("language_reset", function () {
      grpc_client.language_reset({ 'user': "" + socket.id }, function (err, resp) {

      })
    });

    socket.on("disconnect", () => {
      if (socket.id in userCalls) {
        userCalls[socket.id].end()
        delete userCalls[socket.id]
      }
      grpc_client.disconnect({ 'user': socket.id }, function (err, resp) { })
    });

    socket.on("mic_data", function (chunk, language, speaking) {
      let user = socket.id;
      let message = make_message(chunk, user, speaking, language);
      userCalls[user].write(message)
      // console.log(user, "sent")
    });
  });

  startServer();
}

main();
// startServer();

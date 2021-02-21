// const sockjs = require('sockjs');

// const createSocketServer = (httpServer) => {
//     const socketServer = sockjs.createServer({ prefix:'/socket' });
//     socketServer.on('connection', function(conn) {
        
//         conn.on('data', function(message) {
            
//         });
//         conn.on('close', function() {

//         });
//     });
//     socketServer.attach(httpServer);
// };

const MAX_SOCKET_CONNECTIONS = process.env.MAX_CONNECTIONS || 80;
const GrpcClient = require('./grpc_client');


function onUserConnected(io, socket, grpc_client) {
    userCalls[socket.id] = grpc_client.recognizeAudio();
    userCalls[socket.id].on("data", (response)=>onResponse(io, response));
    io.to(socket.id).emit("connect-success", "");
}

const idDict = {};
const userCalls = {};

function onResponse(io, response) {
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
    if (response.action === "terminate") {
        io.to(response.user).emit("terminate");
    } else {
        io.to(response.user).emit("response", data["transcription"], response.language);
    }
}

function make_message(audio, user, speaking, language = 'en', isEnd) {
    const msg = {
        audio: audio,
        user: user + "",
        language: language,
        speaking: speaking,
        isEnd: isEnd
    };
    return msg;
}

const createSocketServer = (httpsServer) => {
    const io = require("socket.io")(httpsServer);
    io.on("connection", (socket) => {
        let grpc_client = GrpcClient('localhost:55102');
        socket.on("disconnect", () => {
            if (socket.id in userCalls) {
                userCalls[socket.id].end();
                delete userCalls[socket.id];
                grpc_client.close();
            }
        });

        const numUsers = socket.client.conn.server.clientsCount;
        if (numUsers > MAX_SOCKET_CONNECTIONS) {
            socket.emit("abort");
            socket.disconnect();
            return;
        }

        onUserConnected(io, socket, grpc_client);

        socket.on("mic_data", function (chunk, language, speaking, isEnd) {
            let user = socket.id;
            let message = make_message(chunk, user, speaking, language, isEnd);
            userCalls[user].write(message)
        });
    });
}

module.exports = createSocketServer;

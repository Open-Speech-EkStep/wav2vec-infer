"use strict";
require('dotenv').config();
var express = require("express");
const app = express();
app.use(express.json());
app.use(express.urlencoded({extended: true}));
const server = require("http").createServer(app);
const path = require("path");
const fs = require("fs");
const {addFeedback, getFeedback} = require('./dbOperations');
app.use(express.static(path.join(__dirname, "static")));
const {uploadFile} = require('./uploader');


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
    const upload = multer({storage: multerStorage});
    app.use(upload.single('audio_data'));
    app.get("/", function (req, res) {
        res.redirect("https://codmento.com/ekstep/test/indian-english");
    });

    app.get("/feedback", function (req, res) {
        console.log("testing nodemon")
        res.sendFile("feedback.html", {root: __dirname});
    });

    app.get("/:language", function (req, res) {
        res.sendFile("index.html", {root: __dirname});
    });

    app.post("/api/feedback", function (req, res) {
        const file = req.file;
        const {user_id, language, text, rating, feedback, device, browser, date} = req.body;

        uploadFile(file.path, user_id, language)
            .then((uploadResponse) => {
                console.log("responsed")
                const blobName = uploadResponse[0]['metadata']['name'];
                const bucketName = uploadResponse[0]['metadata']['bucket'];
                const audio_path = `https://storage.googleapis.com/${bucketName}/${blobName}`
                addFeedback(user_id, language, audio_path, text, rating, feedback, device, browser, date).then(() => {
                    res.json({"success": true})
                }).catch(err => {
                    console.log("error", err)
                    res.status(500).json({"success": false})
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
        const browserFilter = req.query.browser_filter || '';
        const dateFilter = req.query.date_filter || '';
        getFeedback(start, size, ratingFilter, deviceFilter, browserFilter, dateFilter).then(result => {
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
                res.status(500).json({"success": false})
            }
        })
    })

    const PORT = 9008;
    server.listen(PORT);
    console.log("Listening in port => " + PORT);
}

function main() {
    require('./socket-server')(server);
    startServer();
}

main();

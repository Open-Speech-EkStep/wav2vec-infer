const pgp = require('pg-promise')();
// require('dotenv').config();

const envVars = process.env;
let cn = {
    user: envVars.DB_USER,
    password: envVars.DB_PASS,
    database: envVars.DB_NAME,
    host: envVars.DB_HOST,
    logging: false,
    dialect: 'postgres',
    ssl: false,
    dialectOptions: {
        ssl: false,
    },
    operatorsAliases: false,
};

const db = pgp(cn);

const addFeedbackQuery = 'Insert into inference_feedback("user_id", "language", "audio_path", "text", "rating", "device") values ($1, $2, $3, $4, $5, $6);';
const getFeedbackQuery = 'Select * from inference_feedback order by created_on desc limit $1 offset $2';
const getFeedbackFilterByRating = 'Select * from inference_feedback where rating=$1 order by created_on desc limit $2 offset $3';
const getFeedbackFilterByDevice = 'Select * from inference_feedback where device ILIKE $1 order by created_on desc limit $2 offset $3';
const getFeedbackCountQuery = 'Select count(*) as num_feedback from inference_feedback';

const getFeedbackCount = () => {
    return db.one(getFeedbackCountQuery)
}

const getErrorPromise = (error) => {
    return new Promise((resolve, reject) => {
        reject(error)
    })
}

const getSuccessPromise = (data) => {
    return new Promise((resolve, reject) => {
        resolve(data)
    })
}


const addFeedback = (user_id, language, audio_path, text, rating, device) => {
    return db.none(addFeedbackQuery, [
        user_id,
        language,
        audio_path,
        text,
        rating,
        device
    ])
}

const getFeedback = (offset, size = 10, ratingFilter, deviceFilter) => {
    return getFeedbackCount().then(count => {
        let query = getFeedbackQuery;
        let params = [size, offset];
        if(ratingFilter && ratingFilter !== ''){
            query = getFeedbackFilterByRating;
            params = [ratingFilter, size, offset];
        }
        if(deviceFilter && deviceFilter !== ''){
            query = getFeedbackFilterByDevice;
            params = [deviceFilter+"%", size, offset];
        }
        return db.many(query, params).then(result => {
            let total = count['num_feedback'];
            return getSuccessPromise({ "total": total, "data": result ,"filtered": total})
        }).catch(error => getErrorPromise(error))
    }).catch(error => {
        return getErrorPromise(error)
    })
}



module.exports = {
    addFeedback,
    getFeedback
}
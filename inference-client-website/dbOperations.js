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

const addFeedbackQuery = 'Insert into inference_feedback("user_id", "language", "audio_path", "text", "rating","feedback","device","browser") values ($1, $2, $3, $4, $5, $6, $7, $8);';
const getFeedbackQuery = 'Select * from inference_feedback order by created_on desc limit $1 offset $2';
const getFeedbackFilterByRating = 'Select * from inference_feedback where rating=$1 order by created_on desc limit $2 offset $3';
const getFeedbackFilterByRatingCount = 'Select count(*) as num_feedback from inference_feedback where rating=$1 limit $2 offset $3';
const getFeedbackFilterByDevice = 'Select * from inference_feedback where device ILIKE $1 order by created_on desc limit $2 offset $3';
const getFeedbackFilterByDeviceCount = 'Select count(*) as num_feedback from inference_feedback where device ILIKE $1 limit $2 offset $3';
const getFeedbackFilterByRatingAndDevice = 'Select * from inference_feedback where rating=$1 and device ILIKE $2 order by created_on desc limit $3 offset $4';
const getFeedbackFilterByRatingAndDeviceCount = 'Select count(*) as num_feedback from inference_feedback where rating=$1 and device ILIKE $2 limit $3 offset $4';
const getFeedbackCountQuery = 'Select count(*) as num_feedback from inference_feedback';

const getCount = (query, params) => {
    return db.one(query, params)
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


const addFeedback = (user_id, language, audio_path, text, rating, feedback, device, browser) => {
    return db.none(addFeedbackQuery, [
        user_id,
        language,
        audio_path,
        text,
        rating,
        feedback,
        device,
        browser
    ])
}

const getFeedback = async (offset, size = 10, ratingFilter, deviceFilter) => {
    const totalCountJSON = await getCount(getFeedbackCountQuery, []);
    let totalCount = totalCountJSON['num_feedback'];
    let filteredCount = totalCount;
    let query = getFeedbackQuery;
    let params = [size, offset];
    const ratingCondition = ratingFilter && ratingFilter !== '';
    const deviceCondition = deviceFilter && deviceFilter !== '';
    if (ratingCondition && deviceCondition) {
        query = getFeedbackFilterByRatingAndDevice;
        params = [ratingFilter, deviceFilter, size, offset];
        let rdCountJSON = await getCount(getFeedbackFilterByRatingAndDeviceCount, params);
        filteredCount = rdCountJSON['num_feedback'];
    } else if (ratingCondition) {
        query = getFeedbackFilterByRating;
        params = [ratingFilter, size, offset];
        console.log(query, params)
        let rCountJSON = await getCount(getFeedbackFilterByRatingCount, params);
        console.log("RR", rCountJSON)
        filteredCount = rCountJSON['num_feedback'];
    } else if (deviceCondition) {
        query = getFeedbackFilterByDevice;
        params = [deviceFilter + "%", size, offset];
        let dCountJSON = await getCount(getFeedbackFilterByDeviceCount, params);
        filteredCount = dCountJSON['num_feedback'];
    }
    console.log(query, params)
    return db.many(query, params).then(result => {
        console.log(totalCount, filteredCount);
        return getSuccessPromise({"total": totalCount, "data": result, "filtered": filteredCount})
    }).catch(error => getErrorPromise(error))
}

module.exports = {
    addFeedback,
    getFeedback
}

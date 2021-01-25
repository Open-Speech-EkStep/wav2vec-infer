const { Storage } = require('@google-cloud/storage');
const storage = new Storage();

function uploadFile(filePath, userId, language) {
    if (!userId) {
        userId = "unknown";
    }
    const fileName = filePath.replace('uploads/','');
    // console.log(filePath, fileName);
    return storage.bucket(process.env.BUCKET_NAME).upload(filePath, { destination: `feedback/${userId}/${language}/${fileName}` });
}
module.exports = {
    uploadFile
}